from fab_deploy2.tasks import ServiceContextTask, task_method


class Solr(ServiceContextTask):
    """
    Install Solr
    """

    name = 'setup'
    remote_config_path = '/etc/solr/solr.xml'
    remote_schema_path = '/etc/solr/conf/schema.xml'
    context_name = 'solr'

    default_context = {
        'log_dir': '/var/log/solr/',
        'config_dir': '/etc/solr/conf/',
        'schema_template': 'solr/schema.xml',
        'config_template': 'solr/solr.xml',
    }

    @task_method
    def setup(self, template=None, directory=None):
        self._install_package()
        self._setup_logging()
        self._setup_dirs()
        self._setup_schema(template=template, directory=directory)
        self._setup_config(template=template, directory=directory)
        # functions.execute_if_exists('collectd.install_plugin', 'solr')

    @task_method
    def update(self, template=None, directory=None):
        self._setup_config(template=template, directory=directory)

    def _install_package(self):
        raise NotImplementedError()

    def _setup_logging(self):
        raise NotImplementedError()
