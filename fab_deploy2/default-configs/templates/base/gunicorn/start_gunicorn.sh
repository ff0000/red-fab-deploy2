# Customize this script if need to launch a configurable conf file. EI: -c `hostname`.py
{% block def_command %}
{% if gunicorn.use_wsgi %}
COMMAND="{{ python.location }}bin/gunicorn {% if gunicorn.daemonize %}-D{% endif %} -c {{ gunicorn.config_location }} wsgi"
{% else %}
COMMAND="{{ python.location }}bin/gunicorn_django {% if gunicorn.daemonize %}-D{% endif %} -c {{ gunicorn.config_location }}"
{% endif %}
{% endblock %}

{% block newrelic_setup %}
{% if newrelic %}
# New Relic enviroment variables - do NOT rename!
NEW_RELIC_ENVIRONMENT="{{ newrelic.environment }}"
NEW_RELIC_CONFIG_FILE="{{ newrelic.config }}"

# New Relic startup script
NEW_RELIC_ADMIN="{{ python.location }}bin/newrelic-admin"

if [ -f $NEW_RELIC_CONFIG_FILE ] && [ -f $NEW_RELIC_ADMIN ]
then
    export NEW_RELIC_ENVIRONMENT
    export NEW_RELIC_CONFIG_FILE
    exec $NEW_RELIC_ADMIN run-program $COMMAND
else
    exec $COMMAND
fi
{% else %}
    exec $COMMAND
{% endif %}
{% endblock %}
