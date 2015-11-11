import logging
import oslo_messaging
import socket

from oslo_config import cfg
from oslo_messaging import exceptions
from oslo_messaging.notify import notifier
from oslo_messaging.notify import messaging

_OPTS = [
    cfg.ListOpt('multicast_events',
               help='A comma list of configuration property keys which define '
                    'the broadcast targets for multicast notifications. Each '
                    'string in this list should refer to a configuration '
                    'property which itself is a comma list of topic to '
                    'multicast on.',
               default=[]),
    cfg.StrOpt('publisher_id',
               help='The publisher ID to use in the notifications multicasted '
                    'from the driver.',
               default=None),
    cfg.StrOpt('multicast_topic_prefix',
               help='A topic prefix to use for all topics defined in the'
                    'multicast events.',
               default=None)
]
LOG = logging.getLogger(__name__)


class MessagingConfiguration(exceptions.MessagingException):
    def __init__(self, msg):
        msg = "Invalid configuration file: %s" % msg
        super(MessagingConfiguration, self).__init__(msg)


class AMQPMulticastDriver(messaging.MessagingDriver):
    """
    An oslo messaging notification driver which extends the AMQP based
    messaging driver in oslo to support multicasting of notifications
    to a set of exchanges.

    This driver is registered as 'messaging-multicast' in the setup.cfg
    and therefore you can use this driver as a drop-in for any openstack
    service notifications which use oslo messaging.

    To setup:
    1) Obtain the onmcast project (from git or other).

    2) From the project directory run:
        sudo python setup.py install

    3) Configure your openstack service's conf (for services which use
    oslo messaging's notification framework).

    A sample conf looks something like:

        rpc_backend = rabbit
        ...
        transport_url = rabbit://guest:thepass@11.9.232.200:5672/
        notification_driver = messaging-multicast
        multicast_events = image.upload,image.delete
        multicast_topic_prefix = glance.repl.
        publisher_id = GLANCE:MASTER
        image.delete = host1,host2
        image.upload = host1,host2

    The above config will relay glance image.delete and image.upload event type
    messages to the exchanges glance.repl.host1 and glance.repl.host2. NB: The
    standard openstack notification is sent before multicasting is done.

    The multicast event key is matched against the notifications attribute
    values (event_type, priority, etc.) to determine if the event should
    multicast to the specified topics. More details on the message attributes
    to match against see the _message_filter method.

    """

    def __init__(self, conf, topics, transport):
        super(AMQPMulticastDriver, self).__init__(conf, topics, transport)
        conf.register_opts(_OPTS)
        LOG.info("Loading '%s' with events: %s"
                 % (self.__class__.__name__, conf.multicast_events))

        self._id = conf.publisher_id or "%s-MULTICAST" % socket.gethostname()
        self._topic_prefix = conf.multicast_topic_prefix or ''

        self._transport = oslo_messaging.get_transport(conf)
        if not self._transport:
            raise MessagingConfiguration("no oslo messaging transport "
                                         "configured")

        if not conf.multicast_events:
            raise MessagingConfiguration("no 'multicast_events' configured")

        self._notifiers = {}
        self._events = {}
        for event_key in conf.multicast_events:
            event_key = event_key.lower()

            if self._events.get(event_key):
                raise MessagingConfiguration("event '%s' defined multiple "
                                             "times" % event_key)

            conf.register_opts([cfg.ListOpt(event_key, default=[])])

            publishers = []
            for topic in set(conf[event_key]):
                topic = "%s%s.%s" % (self._topic_prefix, topic, event_key)
                publisher = self._notifiers.get(topic)
                if not publisher:
                    publisher = notifier.Notifier(self._transport,
                                                  publisher_id=self._id,
                                                  driver='messaging',
                                                  topic=topic)
                    self._notifiers[topic] = publisher
                publishers.append(publisher)

            self._events[event_key] = publishers
            LOG.info("Registered %s topics for event type: %s"
                     % (len(publishers), event_key))

    def _topic_for_notifier(self, topic_notifier):
        for topic, _notifier in self._notifiers.items():
            if _notifier == topic_notifier:
                return topic
        return None

    def _notify_list(self, notifiers, ctxt, event_type, msg, priority):
        for publisher in notifiers:
            method = getattr(publisher, priority.lower(), None)
            if method and hasattr(method, '__call__'):
                LOG.debug("Multicasting '%s' to: %s"
                          % (event_type,
                             self._topic_for_notifier(publisher)))
                method(ctxt, event_type, msg)
            else:
                LOG.warn("Notifier '%s' does not support: %s"
                         % (publisher, priority))

    def _message_filter(self, msg):
        return [msg.get(k).lower() for k in ['event_type', 'priority',
                                             'message_id', 'publisher_id']]

    def notify(self, ctxt, msg, priority, retry):
        _notify = super(AMQPMulticastDriver, self).notify(
            ctxt, msg, priority, retry)

        _filter = self._message_filter(msg)
        for event, notifiers in self._events.items():
            if event in _filter:
                self._notify_list(notifiers, ctxt, event,
                                  msg, priority)

        return _notify
