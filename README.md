# agent-loop
Repository for some demo agent loops using Claude API (and maybe others in the future)

This project is for learning purposes only. As I've been experimenting with LLM APIs, typically Claude. 

This started off as a simple "hello world" type app, but more like "hello Claude". For now
I've built mock tools, a weather service and a time service. Using the tools I can prompt Claude
to tell me the weather and time and it should use the tools provided. All this wrapped in a loop.

This is again just for testing and not a production ready solution. It would need to handle more cases
and have better error handling. But we'll see if I get bored one weekend I might extend this to something
more useful.

# Running
You do need an Anthropic key

Then set it to an environment variable called ANTHROPIC_API_KEY

Now just run the script, here is a prompt that will typically force at least two tool call loops:

```What's the weather in Paris? If it's above 20 degrees, check Tokyo's weather too. What time is it wherever you checked?```

# Future Ideas
These are all just for learning purposes since they all exist already but are thing I want to better understand:
* ~~Add MCP support for tools~~ Added a weather MCP server (for now running locally)
* ~~Allow continuous chat rather than just single prompt execution~~
* ~~Verify the output, maybe implement some basic guardrails~~ (not exactly verified but added some guardrails in the system prompt, probably can go further

# MCP Addition
I added an MCP server support, MCP servers can be for now can be configured in [resources/mcp.json](resources/mcp.json).

For testing I'm using this server: https://github.com/mattr9124/weather-mcp-server-java -
I went with Java since that's what I know best. There are npm variants that would probably work just as well. 

This now has a hybrid of inline tools and MCP tools.
