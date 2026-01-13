# plugin_system.py

class PluginSystem:
    def __init__(self):
        self.plugins = []

    def register_plugin(self, plugin):
        self.plugins.append(plugin)
        print(f"Plugin registered: {plugin.__class__.__name__}")

    def run_plugins(self, *args, **kwargs):
        for plugin in self.plugins:
            plugin.run(*args, **kwargs)

# Example plugin
class ExamplePlugin:
    def run(self, *args, **kwargs):
        print("Example plugin running.")

if __name__ == "__main__":
    ps = PluginSystem()
    ps.register_plugin(ExamplePlugin())
    ps.run_plugins()
