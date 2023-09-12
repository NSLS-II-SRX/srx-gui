How to Manually Test the GUI with Simulated Profile Collection
==============================================================

1. Install the package in develop mode::

    $ pip install -e .
    $ pip install -r requirements-dev.txt

2. Start Kafka Docker container (in a separate terminal)::

    $ cd <root>/srx_gui/tests/config
    $ sudo docker-compose -f bitnami-kafka-docker-compose.yml u

3. Start the Queue Server using simulated profile collection, which is part of the repository::

    $ start-re-manager --startup-dir=<root>/srx_gui/tests/startup --keep-re --zmq-publish-console=ON

   or stand-alone simulated profile collection (copy files from ``<root>/srx_gui/tests/startup``
   to ``~/.ipython/profile_srx_sim/startup``)::

    $ start-re-manager --startup-profile=srx_sim --keep-re --zmq-publish-console=ON

   or using IPython kernel::

    $ start-re-manager --startup-profile=srx_sim --keep-re --use-ipython-kernel=ON --zmq-publish-console=ON

4. Start SRX GUI::

    $ srx-gui --kafka-config-path=<root>/srx_gui/tests/config/kafka.yml --kafka-topics=srx.bluesky.runengine.documents

5. Test the GUI using the plan ``nano_scan_and_fly`` with the parameters such as ``[0, 1, 15, 0, 2, 5, 0.1]``.
   Adding `kwarg` ``{"snaking": True}`` emulates scan with snaking.
