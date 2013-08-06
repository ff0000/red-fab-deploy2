{% block def_command %}
COMMAND="{{ python.location }}bin/python {{ code_path }}/project/manage.py celeryd"
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
