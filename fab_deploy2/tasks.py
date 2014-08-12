import sys
import inspect
import types
from functools import wraps

from fabric.tasks import Task, WrappedCallableTask
from fabric.api import env, settings

from . import functions


class PlatformCallableTask(WrappedCallableTask):
    def __init__(self, callable, platform, *args, **kwargs):
        self.env_kwargs = {}
        if platform:
            self.env_kwargs = { 'current_platform' : platform }
        super(PlatformCallableTask, self).__init__(callable, *args, **kwargs)

    def run(self, *args, **kwargs):
        with settings(**self.env_kwargs):
            return super(PlatformCallableTask, self).run(*args, **kwargs)

def task_method(*args, **kwargs):
    """
    Decorator declaring the wrapped method to be task.

    It accepts the same arguments as ``fabric.decorators.task`` so
    use it on methods just like fabric's decorator is used on functions.

    Tasks are run with a blank task_context attribute added to the
    env varible that is unique for that task. This can be used to
    overide context or store calculated values for the duration of
    a task run.

    The class decorated method belongs to should be a subclass
    of :class:`.MultiTask`.
    """

    invoked = bool(not args or kwargs)
    if not invoked:
        func, args = args[0], ()

    def decorator(func):
        @wraps(func)
        def f(*a, **k):
            with settings(task_context={}):
                return func(*a, **k)
        f._task_info = dict(
            args = args,
            kwargs = kwargs
        )
        return f

    return decorator if invoked else decorator(func)

class MultiTask(object):
    """
    A MultiTask is a class that has multiple runnable tasks.

    Each method that should be a task must be marked with the
    task_method decorator.


    The tasks from an instance are registered by calling the
    as_tasks method.

    ei: MyTask().as_tasks()
    """

    def _get_module_obj(self, parent=None, name=None, depth=None):
        if not parent:
            d = 2
            if depth:
                d = d + depth
            frm = inspect.stack()[d]
            mod = inspect.getmodule(frm[0])
            parent = sys.modules[mod.__name__]
        else:
            assert name

        if name:
            module_obj = types.ModuleType(name)
            setattr(parent, name, module_obj)
            return module_obj
        else:
            return parent

    def as_tasks(self, parent=None, name=None):
        """
        Called to register this instaces tasks with fabric.


        :param parent: A module that you want to register the tasks on \
        defaults to the module that declares your class.
        :param name: A name to register your tasks on. If provided a dummy \
        module will be created to hold your tasks.
        """
        module_obj = self._get_module_obj(parent=parent, name=name)

        task_list = []
        for name, task in self._get_tasks():
            setattr(module_obj, name, task)
            task_list.append(name)

        return task_list

    def _is_task(self, func):
        return hasattr(func, '_task_info')

    def _task_for_method(self, method):
        return WrappedCallableTask(method, *method._task_info['args'], **method._task_info['kwargs'])

    def _get_tasks(self):
        return (
            (name, self._task_for_method(task))
            for name, task in inspect.getmembers(self, self._is_task)
        )

class _ContextMixin(object):

    def _value_for_default(self, key):
        if hasattr(env, 'task_context') and env.task_context.get(key):
            return env.task_context.get(key)

        context_dict = env.context.get(self.namespace, {})
        role = env.host_roles.get(env.host_string)
        if role:
            role_dict = functions.get_role_context(role)
            if role_dict:
                role_dict = role_dict.get(self.namespace, {})
                context_dict.update(role_dict)

        if key in context_dict:
            return context_dict.get(key)
        else:
            try:
                return object.__getattribute__(self, key)
            except AttributeError:
                return self.default_context.get(key)

    def __getattr__(self, key):
        if self.default_context and key in self.default_context:
            return self._value_for_default(key)
        return object.__getattribute__(self, key)

    def __getattribute__(self, key):
        if key != 'default_context' and key[0] != '_':
            if self.default_context and key in self.default_context:
                return self._value_for_default(key)
        return object.__getattribute__(self, key)

    def get_task_context(self):
        """
        Returns the a context dictionary for this class
        """
        context = {}
        for k, v in self.default_context.items():
            context[k] = getattr(self, k)
        return context

    def get_template_context(self):
        """
        Returns the a context dictionary that should be
        passed to templates rendered by this class.

        Returns a dictionary with a key of self.context_name
        and a value of the results of `get_task_context`.
        Can be overridden to include context from other tasks.
        """
        all_context = {}
        context = self.get_task_context()
        all_context[self.context_name] = context
        return all_context

class ContextTask(Task, _ContextMixin):
    """
    A context aware task.

    Attributes declared in the self.default_context
    dictionary can be overiden at multiple levels. The following
    is the order in which the final value for an attribute is resolved.

    1) env.task_context for just the key value. This attribute is
       reset on every new task that is called.
    2) Matching key in env.context[roll_name][self.namespace]
    3) Matching dictionary in env.context[self.namespace]
    4) Class attribute
    5) Default value from self.default_context

    The final value for that varible can always be accessed
    on the instance ei: self.foo.

    The attribute used to lookup global or role overides
    is self.namespace. This defaults to self.context_name.

    self.context_name is the prefix that will be used
    in templates to refer to the context generated by this
    class.
    """

    context_name = None
    namespace = None
    default_context = None

    def __init__(self, *args, **kwargs):
        super(ContextTask, self).__init__(*args, **kwargs)
        if not self.namespace:
            self.namespace = self.context_name

class MultiContextTask(MultiTask, _ContextMixin):
    """
    A context aware multi task.

    Multitask are classes whose methods can ask as context tasks.
    This is done by using the task_method decorator.
    """

    context_name = None
    namespace = None
    default_context = None

    def __init__(self, *args, **kwargs):
        super(MultiContextTask, self).__init__(*args, **kwargs)
        if not self.namespace:
            self.namespace = self.context_name

    @task_method
    def context(self):
        """
        Returns the context dictionary for this task.
        """
        return self.get_task_context()

class ServiceContextTask(MultiTask, _ContextMixin):
    """
    A context aware multi task.

    An interface that provides a start, stop and update tasks.
    """

    context_name = None
    namespace = None
    default_context = None

    def __init__(self, *args, **kwargs):
        super(ServiceContextTask, self).__init__(*args, **kwargs)
        if not self.namespace:
            self.namespace = self.context_name

    @task_method
    def start(self):
        """
        Starts or restarts service
        """
        raise NotImplementedError()

    @task_method
    def stop(self):
        """
        Stops service
        """
        raise NotImplementedError()

    @task_method
    def update(self):
        """
        Updates service

        Shouldn't restart anything
        """
        raise NotImplementedError()

    @task_method
    def context(self):
        """
        Returns the context dictionary for this task.
        """
        return self.get_task_context()
