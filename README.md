# onmcast
An oslo-messaging based notification driver which permits selective
multicasting based on notification event values. This driver is a
drop-in replacement for any OpenStack service which supports
oslo-messaging notifications (basically all OpenStack services) and
can be used to conditionally replicate notification events to your
choice of exchange(s) and publisher ID.

Please note this is a toy and has not been tested in production
environments. Moreover this is a bare-bones implementation; it
could easily be extended to permit additional features such as
conditional event selection with multiple "selectors" (e.g. regex,
contains, etc.).


## Basic Usage

When installed, this driver registers itself as ```messaging-multicast```
for the ```oslo.messaging.notify.drivers``` extension and can then
be specified in your OpenStack services conf as the notification driver.

### To setup:

1. Obtain the onmcast project via github or other.

2. From the onmcast project repo directory, run the following to install it:
    ```sudo python setup.py install```

3. Configure the conf file for the OpenStack service you wish to multicast events for.


### Supported configuration properties

```multicast_events``` A comma list of configuration property keys
which define the broadcast targets for multicast notifications. Each
string in this list should refer to a configuration property which
itself is a comma list of topics to multicast on.

```publisher_id``` The publisher ID to use in the event notifications
which are multicasted.

```multicast_topic_prefix``` A topic prefix to use for all topics defined
in the multicast events.


A sample config snippet when integrated with glance looks something like this:

```ini
rpc_backend = rabbit
transport_url = rabbit://guest:thepass@11.9.232.200:5672/
notification_driver = messaging-multicast
multicast_events = image.upload,image.delete
multicast_topic_prefix = glance.repl.
publisher_id = GLANCE:MASTER
image.delete = host1,host2
image.upload = host1,host2
```

The above config will relay glance ```image.delete``` and ```image.upload``` event type
messages to the exchanges ```glance.repl.host1``` and ```glance.repl.host2```.
NB: The standard openstack notification is sent before multicasting is done.

The multicast event key is matched against the notifications attribute
values (```event_type```, ```priority```, etc.) to determine if the event should
multicast to the specified topics. More details on the message attributes
to match against see the ```_message_filter()``` method of the driver.

