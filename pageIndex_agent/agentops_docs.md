Core Concepts
Understanding the fundamental concepts of AgentOps

​
The AgentOps SDK Architecture
AgentOps is designed to provide comprehensive monitoring and analytics for AI agent workflows with minimal implementation effort. The SDK follows these key design principles:
​
Automated Instrumentation
After calling agentops.init(), the SDK automatically identifies installed LLM providers and instruments their API calls. This allows AgentOps to capture interactions between your code and the LLM providers to collect data for your dashboard without requiring manual instrumentation for every call.
​
Declarative Tracing with Decorators
The decorators system allows you to add tracing to your existing functions and classes with minimal code changes. Decorators create hierarchical spans that provide a structured view of your agent’s operations for monitoring and analysis.
​
OpenTelemetry Foundation
AgentOps is built on OpenTelemetry, a widely-adopted standard for observability instrumentation. This provides a robust and standardized approach to collecting, processing, and exporting telemetry data.
​
Sessions
A Session represents a single user interaction with your agent. When you initialize AgentOps using the init function, a session is automatically created for you:
import agentops

# Initialize AgentOps with automatic session creation
agentops.init(api_key="YOUR_API_KEY")
By default, all events and API calls will be associated with this session. For more advanced use cases, you can control session creation manually:
# Initialize without auto-starting a session
agentops.init(api_key="YOUR_API_KEY", auto_start_session=False)

# Later, manually start a session when needed
agentops.start_session(tags=["customer-query"])
​
Span Hierarchy
In AgentOps, activities are organized into a hierarchical structure of spans:
SESSION: The root container for all activities in a single execution of your workflow
AGENT: Represents an autonomous entity with specialized capabilities
WORKFLOW: A logical grouping of related operations
OPERATION/TASK: A specific task or function performed by an agent
LLM: An interaction with a language model
TOOL: The use of a tool or API by an agent
This hierarchy creates a complete trace of your agent’s execution:
SESSION
  ├── AGENT
  │     ├── OPERATION/TASK
  │     │     ├── LLM
  │     │     └── TOOL
  │     └── WORKFLOW
  │           └── OPERATION/TASK
  └── LLM (unattributed to a specific agent)
​
Agents
An Agent represents a component in your application that performs tasks. You can create and track agents using the @agent decorator:
from agentops.sdk.decorators import agent, operation

@agent(name="customer_service")
class CustomerServiceAgent:
    @operation
    def answer_query(self, query):
        # Agent logic here
        pass
​
LLM Events
AgentOps automatically tracks LLM API calls from supported providers, collecting valuable information like:
Model: The specific model used (e.g., “gpt-4”, “claude-3-opus”)
Provider: The LLM provider (e.g., “OpenAI”, “Anthropic”)
Prompt Tokens: Number of tokens in the input
Completion Tokens: Number of tokens in the output
Cost: The estimated cost of the interaction
Messages: The prompt and completion content
import agentops
from openai import OpenAI

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

# Initialize the OpenAI client
client = OpenAI()

# This LLM call is automatically tracked
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's the capital of France?"}]
)
​
Tags
Tags help you organize and filter your sessions. You can add tags when initializing AgentOps or when starting a session:
# Add tags when initializing
agentops.init(api_key="YOUR_API_KEY", tags=["production", "web-app"])

# Or when manually starting a session
agentops.start_session(tags=["customer-service", "tier-1"])
​
Host Environment
AgentOps automatically collects basic information about the environment where your agent is running:
Operating System: The OS type and version
Python Version: The version of Python being used
Hostname: The name of the host machine (anonymized)
SDK Version: The version of the AgentOps SDK being used
​
Dashboard Views
The AgentOps dashboard provides several ways to visualize and analyze your agent’s performance:
Session List: Overview of all sessions with filtering options
Timeline View: Chronological display of spans showing duration and relationships
Tree View: Hierarchical representation of spans showing parent-child relationships
Message View: Detailed view of LLM interactions with prompt and completion content
Analytics: Aggregated metrics across sessions and operations
​
Putting It All Together
A typical implementation looks like this:
import agentops
from openai import OpenAI
from agentops.sdk.decorators import agent, operation

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY", tags=["production"])

# Define an agent
@agent(name="assistant")
class AssistantAgent:
    def __init__(self):
        self.client = OpenAI()
    
    @operation
    def answer_question(self, question):
        # This LLM call will be automatically tracked and associated with this agent
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": question}]
        )
        return response.choices[0].message.content

def workflow():
    # Use the agent
    assistant = AssistantAgent()
    answer = assistant.answer_question("What's the capital of France?")
    print(answer)

workflow()
# Session is automatically tracked until application terminates

Decorators
Use decorators to track activities in your agent system

​
Available Decorators
AgentOps provides the following decorators:
Decorator	Purpose	Creates
@session	Track an entire user interaction	SESSION span
@agent	Track agent classes and their lifecycle	AGENT span
@operation	Track discrete operations performed by agents	OPERATION span
@workflow	Track a sequence of operations	WORKFLOW span
@task	Track smaller units of work (similar to operations)	TASK span
@tool	Track tool usage and cost in agent operations	TOOL span
@guardrail	Track guardrail input and output	GUARDRAIL span
​
Decorator Hierarchy
The decorators create spans that form a hierarchy:
SESSION
  ├── AGENT
  │     ├── OPERATION or TASK
  │     │     ├── LLM
  │     │     └── TOOL
  │     └── WORKFLOW
  │           └── OPERATION or TASK
  └── AGENT
        └── OPERATION or TASK
​
Using Decorators
​
@session
The @session decorator tracks an entire user interaction from start to finish:
from agentops.sdk.decorators import session
import agentops

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@session
def answer_question(question):
    # Create and use agents
    weather_agent = WeatherAgent()
    result = weather_agent.get_forecast(question)
    
    # Return the final result
    return result
Each @session function call creates a new session span that contains all the agents, operations, and workflows used during that interaction.
​
@agent
The @agent decorator instruments a class to track its lifecycle and operations:
from agentops.sdk.decorators import agent, operation
import agentops

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@agent
class WeatherAgent:
    def __init__(self):
        self.api_key = "weather_api_key"
        
    @operation
    def get_forecast(self, location):
        # Get weather data
        return f"The weather in {location} is sunny."

def check_weather(city):
    weather_agent = WeatherAgent()
    forecast = weather_agent.get_forecast(city)
    return forecast

weather_info = check_weather("San Francisco")
When an agent-decorated class is instantiated within a session, an AGENT span is created automatically.
​
@operation
The @operation decorator tracks discrete functions performed by an agent:
from agentops.sdk.decorators import agent, operation
import agentops

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@agent
class MathAgent:
    @operation
    def add(self, a, b):
        return a + b
        
    @operation
    def multiply(self, a, b):
        return a * b

def calculate(x, y):
    math_agent = MathAgent()
    sum_result = math_agent.add(x, y)
    product_result = math_agent.multiply(x, y)
    return {"sum": sum_result, "product": product_result}

results = calculate(5, 3)
Operations represent the smallest meaningful units of work in your agent system. Each operation creates an OPERATION span with:
Inputs (function arguments)
Output (return value)
Duration
Success/failure status
​
@workflow
The @workflow decorator tracks a sequence of operations that work together:
from agentops.sdk.decorators import agent, operation, workflow
import agentops

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@agent
class TravelAgent:
    def __init__(self):
        self.flight_api = FlightAPI()
        self.hotel_api = HotelAPI()
    
    @workflow
    def plan_trip(self, destination, dates):
        # This workflow contains multiple operations
        flights = self.find_flights(destination, dates)
        hotels = self.find_hotels(destination, dates)
        
        return {
            "flights": flights,
            "hotels": hotels
        }
        
    @operation
    def find_flights(self, destination, dates):
        return self.flight_api.search(destination, dates)
        
    @operation
    def find_hotels(self, destination, dates):
        return self.hotel_api.search(destination, dates)
Workflows help you organize related operations and see their collective performance.
​
@task
The @task decorator is similar to @operation but can be used for smaller units of work:
from agentops.sdk.decorators import agent, task
import agentops

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@agent
class DataProcessor:
    @task
    def normalize_data(self, data):
        # Normalize the data
        return [x / sum(data) for x in data]
    
    @task
    def filter_outliers(self, data, threshold=3):
        # Filter outliers
        mean = sum(data) / len(data)
        std_dev = (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5
        
        return [x for x in data if abs(x - mean) <= threshold * std_dev]
The @task and @operation decorators function identically (they are aliases in the codebase), and you can choose the one that best fits your semantic needs.
​
@tool
The @tool decorator tracks tool usage within agent operations and supports cost tracking. It works with all function types: synchronous, asynchronous, generator, and async generator.
from agentops.sdk.decorators import agent, tool
import asyncio

@agent
class ProcessingAgent:
    def __init__(self):
        pass

    @tool(cost=0.01)
    def sync_tool(self, item):
        """Synchronous tool with cost tracking."""
        return f"Processed {item}"

    @tool(cost=0.02)
    async def async_tool(self, item):
        """Asynchronous tool with cost tracking."""
        await asyncio.sleep(0.1)
        return f"Async processed {item}"

    @tool(cost=0.03)
    def generator_tool(self, items):
        """Generator tool with cost tracking."""
        for item in items:
            yield self.sync_tool(item)

    @tool(cost=0.04)
    async def async_generator_tool(self, items):
        """Async generator tool with cost tracking."""
        for item in items:
            await asyncio.sleep(0.1)
            yield await self.async_tool(item)
The tool decorator provides:
Cost tracking for each tool call
Proper span creation and nesting
Support for all function types (sync, async, generator, async generator)
Cost accumulation in generator and async generator operations
​
@guardrail
The @guardrail decorator tracks guardrail input and output. You can specify the guardrail type ("input" or "output") with the spec parameter.
from agentops.sdk.decorators import guardrail
import agentops
import re

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@guardrail(spec="input")
def secret_key_guardrail(input):
    pattern = r'\bsk-[a-zA-Z0-9]{10,}\b'
    result = True if re.search(pattern, input) else False
    return {
        "tripwire_triggered" : result
    }
​
Decorator Attributes
You can pass additional attributes to decorators:
from agentops.sdk.decorators import agent, operation
import agentops

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@agent(name="custom_agent_name", attributes={"version": "1.0"})
class CustomAgent:
    @operation(name="custom_operation", attributes={"importance": "high"})
    def process(self, data):
        return data
Common attributes include:
Attribute	Description	Example
name	Custom name for the span	name="weather_forecast"
attributes	Dictionary of custom attributes	attributes={"model": "gpt-4"}
​
Complete Example
Here’s a complete example using all the decorators together:
from agentops.sdk.decorators import session, agent, operation, workflow, task
import agentops

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

@session
def assist_user(query):
    # Create the main assistant
    assistant = Assistant()
    
    # Process the query
    return assistant.process_query(query)

@agent
class Assistant:
    def __init__(self):
        pass
    
    @workflow
    def process_query(self, query):
        research_agent = ResearchAgent()
        writing_agent = WritingAgent()
        
        # Research phase
        research = research_agent.gather_information(query)
        
        # Writing phase
        response = writing_agent.generate_response(query, research)
        
        return response

@agent
class ResearchAgent:
    @operation
    def gather_information(self, query):
        # Perform web search
        search_results = self.search(query)
        
        # Analyze results
        return self.analyze_results(search_results)
    
    @task
    def search(self, query):
        # Simulate web search
        return [f"Result for {query}", f"Another result for {query}"]
    
    @task
    def analyze_results(self, results):
        # Analyze search results
        return {"summary": "Analysis of " + ", ".join(results)}

@agent
class WritingAgent:
    @operation
    def generate_response(self, query, research):
        # Generate a response based on the research
        return f"Answer to '{query}' based on: {research['summary']}"

assist_user("What is the capital of France?")
In this example:
The @session decorator wraps the entire interaction
The @agent decorator defines multiple agent classes
The @workflow decorator creates a workflow that coordinates agents
The @operation and @task decorators track individual operations
All spans are properly nested in the hierarchy
Note that LLM and TOOL spans are automatically created when you use compatible LLM libraries or tool integrations.
​
Best Practices
Use @session for top-level functions that represent complete user interactions
Apply @agent to classes that represent distinct components of your system
Use @operation for significant functions that represent complete units of work
Use @task for smaller functions that are part of larger operations
Apply @workflow to methods that coordinate multiple operations
Keep decorator nesting consistent with the logical hierarchy of your code
Add custom attributes to provide additional context for analysis
Use meaningful names for all decorated components
​
Dashboard Visualization
In the AgentOps dashboard, decorators create spans that appear in:
Timeline View: Shows the execution sequence and duration
Hierarchy View: Displays the parent-child relationships
Detail Panels: Shows inputs, outputs, and attributes
Performance Metrics: Tracks execution times and success rates
This visualization helps you understand the flow and performance of your agent system.

Traces
Effectively manage traces in your agent workflow

​
Automatic Trace Management
The simplest way to create and manage traces is to use the init function with automatic trace creation:
import agentops

# Initialize with automatic trace creation (default)
agentops.init(api_key="YOUR_API_KEY", default_tags=["production"])
This approach:
Creates a trace automatically when you initialize the SDK
Tracks all events in the context of this trace
Manages the trace throughout the lifecycle of your application
​
Manual Trace Creation
For more control, you can disable automatic trace creation and start traces manually:
import agentops

# Initialize without auto-starting a trace
agentops.init(api_key="YOUR_API_KEY", auto_start_session=False)

# Later, manually start a trace when needed
trace_context = agentops.start_trace(
    trace_name="Customer Workflow", 
    tags=["customer-query", "high-priority"]
)

# End the trace when done
agentops.end_trace(trace_context, end_state="Success")
Manual trace management is useful when:
You want to control exactly when trace tracking begins
You need to associate different traces with different sets of tags
Your application has distinct workflows that should be tracked separately
​
Using the Trace Decorator
You can use the @trace decorator to create a trace for a specific function:
import agentops

@agentops.trace
def process_customer_data(customer_id):
    # This entire function execution will be tracked as a trace
    return analyze_data(customer_id)

# Or with custom parameters
@agentops.trace(name="data_processing", tags=["analytics"])
def analyze_user_behavior(user_data):
    return perform_analysis(user_data)
​
Trace Context Manager
TraceContext objects support Python’s context manager protocol, making it easy to manage trace lifecycles:
import agentops

# Using trace context as a context manager
with agentops.start_trace("user_session", tags=["web"]) as trace:
    # All operations here are tracked within this trace
    process_user_request()
    # Trace automatically ends when exiting the context
    # Success/Error state is set based on whether exceptions occurred
​
Trace States
Every trace has an associated state that indicates its completion status. AgentOps provides multiple ways to specify trace end states for flexibility and backward compatibility.
​
AgentOps TraceState Enum (Recommended)
The recommended approach is to use the TraceState enum from AgentOps:
from agentops import TraceState

# Available states
agentops.end_trace(trace_context, end_state=TraceState.SUCCESS)  # Trace completed successfully
agentops.end_trace(trace_context, end_state=TraceState.ERROR)    # Trace encountered an error
agentops.end_trace(trace_context, end_state=TraceState.UNSET)    # Trace state is not determined
​
OpenTelemetry StatusCode
For advanced users familiar with OpenTelemetry, you can use StatusCode directly:
from opentelemetry.trace.status import StatusCode

agentops.end_trace(trace_context, end_state=StatusCode.OK)     # Same as TraceState.SUCCESS
agentops.end_trace(trace_context, end_state=StatusCode.ERROR)  # Same as TraceState.ERROR
agentops.end_trace(trace_context, end_state=StatusCode.UNSET)  # Same as TraceState.UNSET
​
String Values
String values are also supported for convenience:
# String representations
agentops.end_trace(trace_context, end_state="Success")        # Maps to SUCCESS
agentops.end_trace(trace_context, end_state="Error")          # Maps to ERROR  
agentops.end_trace(trace_context, end_state="Indeterminate")  # Maps to UNSET
​
State Mapping
All state representations map to the same underlying OpenTelemetry StatusCode:
AgentOps TraceState	OpenTelemetry StatusCode	String Values	Description
TraceState.SUCCESS	StatusCode.OK	”Success”	Trace completed successfully
TraceState.ERROR	StatusCode.ERROR	”Error”	Trace encountered an error
TraceState.UNSET	StatusCode.UNSET	”Indeterminate”	Trace state is not determined
​
Default Behavior
If no end state is provided, the default is TraceState.SUCCESS:
# These are equivalent
agentops.end_trace(trace_context)
agentops.end_trace(trace_context, end_state=TraceState.SUCCESS)
​
Trace Attributes
Every trace collects comprehensive metadata to provide rich context for analysis. Trace attributes are automatically captured by AgentOps and fall into several categories:
​
Core Trace Attributes
Identity and Timing:
Trace ID: A unique identifier for the trace
Span ID: Identifier for the root span of the trace
Start Time: When the trace began
End Time: When the trace completed (set automatically)
Duration: Total execution time (calculated automatically)
User-Defined Attributes:
Trace Name: Custom name provided when starting the trace
Tags: Labels for filtering and grouping (list of strings or dictionary)
End State: Success, error, or unset status
# Tags can be provided as a list of strings or a dictionary
agentops.start_trace("my_trace", tags=["production", "experiment-a"])
agentops.start_trace("my_trace", tags={"environment": "prod", "version": "1.2.3"})
​
Resource Attributes
AgentOps automatically captures system and environment information:
Project and Service:
Project ID: AgentOps project identifier
Service Name: Service name (defaults to “agentops”)
Service Version: Version of your service
Environment: Deployment environment (dev, staging, prod)
SDK Version: AgentOps SDK version being used
Host System Information:
Host Name: Machine hostname
Host System: Operating system (Windows, macOS, Linux)
Host Version: OS version details
Host Processor: CPU architecture information
Host Machine: Machine type identifier
Performance Metrics:
CPU Count: Number of available CPU cores
CPU Percent: CPU utilization at trace start
Memory Total: Total system memory
Memory Available: Available system memory
Memory Used: Currently used memory
Memory Percent: Memory utilization percentage
Dependencies:
Imported Libraries: List of Python packages imported in your environment
​
Span Hierarchy
Nested Operations:
Spans: All spans (operations, agents, tools, workflows) recorded during the trace
Parent-Child Relationships: Hierarchical structure of operations
Span Kinds: Types of operations (agents, tools, workflows, tasks)
​
Accessing Trace Attributes
While most attributes are automatically captured, you can access trace information programmatically:
import agentops

# Start a trace and get the context
trace_context = agentops.start_trace("my_workflow", tags={"version": "1.0"})

# Access trace information
trace_id = trace_context.span.get_span_context().trace_id
span_id = trace_context.span.get_span_context().span_id

print(f"Trace ID: {trace_id}")
print(f"Span ID: {span_id}")

# End the trace
agentops.end_trace(trace_context)
​
Custom Attributes
You can add custom attributes to spans within your trace:
import agentops

with agentops.start_trace("custom_workflow") as trace:
    # Add custom attributes to the current span
    trace.span.set_attribute("custom.workflow.step", "data_processing")
    trace.span.set_attribute("custom.batch.size", 100)
    trace.span.set_attribute("custom.user.id", "user_123")
    
    # Your workflow logic here
    process_data()
​
Attribute Naming Conventions
AgentOps follows OpenTelemetry semantic conventions for attribute naming:
AgentOps Specific: agentops.* (e.g., agentops.span.kind)
GenAI Operations: gen_ai.* (e.g., gen_ai.request.model)
System Resources: Standard names (e.g., host.name, service.name)
Custom Attributes: Use your own namespace (e.g., myapp.user.id)
​
Trace Context
Traces create a context for all span recording. When a span is recorded:
It’s associated with the current active trace
It’s automatically included in the trace’s timeline
It inherits the trace’s tags for filtering and analysis
​
Viewing Traces in the Dashboard
The AgentOps dashboard provides several views for analyzing your traces:
Trace List: Overview of all traces with filtering options
Trace Details: In-depth view of a single trace
Timeline View: Chronological display of all spans in a trace
Tree View: Hierarchical representation of agents, operations, and events
Analytics: Aggregated metrics across traces
​
Best Practices
Start traces at logical boundaries in your application workflow
Use descriptive trace names to easily identify them in the dashboard
Apply consistent tags to group related traces
Use fewer, longer traces rather than many short ones for better analysis
Use automatic trace management unless you have specific needs for manual control
Leverage context managers for automatic trace lifecycle management
Set appropriate end states to track success/failure rates

Spans
Understanding the different types of spans in AgentOps

​
Core Span Types
AgentOps organizes all spans with specific kinds:
Span Kind	Description
SESSION	The root container for all activities in a single execution of your workflow
AGENT	Represents an autonomous entity with specialized capabilities
WORKFLOW	A logical grouping of related operations
OPERATION	A specific task or function performed by an agent
TASK	Alias for OPERATION, used interchangeably
LLM	An interaction with a language model
TOOL	The use of a tool or API by an agent
​
Span Hierarchy
Spans in AgentOps are organized hierarchically:
SESSION
  ├── AGENT
  │     ├── OPERATION/TASK
  │     │     ├── LLM
  │     │     └── TOOL
  │     └── WORKFLOW
  │           └── OPERATION/TASK
  └── LLM (unattributed to a specific agent)
Every span exists within the context of a session, and most spans (other than the session itself) have a parent span that provides context.
​
Span Attributes
All spans in AgentOps include:
ID: A unique identifier
Name: A descriptive name
Kind: The type of span (SESSION, AGENT, etc.)
Start Time: When the span began
End Time: When the span completed
Status: Success or error status
Attributes: Key-value pairs with additional metadata
Different span types have specialized attributes:
​
LLM Spans
LLM spans track interactions with large language models and include:
Model: The specific model used (e.g., “gpt-4”, “claude-3-opus”)
Provider: The LLM provider (e.g., “OpenAI”, “Anthropic”)
Prompt Tokens: Number of tokens in the input
Completion Tokens: Number of tokens in the output
Cost: The estimated cost of the interaction
Messages: The prompt and completion content
​
Tool Spans
Tool spans track the use of tools or APIs and include:
Tool Name: The name of the tool used
Input: The data provided to the tool
Output: The result returned by the tool
Duration: How long the tool operation took
​
Operation/Task Spans
Operation spans track specific functions or tasks:
Operation Type: The kind of operation performed
Parameters: Input parameters to the operation
Result: The output of the operation
Duration: How long the operation took
​
Creating Spans
There are several ways to create spans in AgentOps:
​
Using Decorators
The recommended way to create spans is using decorators:
from agentops.sdk.decorators import agent, operation, session, workflow, task

@session
def my_workflow():
    agent_instance = MyAgent()
    return agent_instance.perform_task()

@agent
class MyAgent:
    @operation
    def perform_task(self):
        # Perform the task
        return result
​
Automatic Instrumentation
AgentOps automatically instruments LLM API calls from supported providers when auto_instrument=True (the default):
import agentops
from openai import OpenAI

# Initialize AgentOps
agentops.init(api_key="YOUR_API_KEY")

# Initialize the OpenAI client
client = OpenAI()

# This LLM call will be automatically tracked
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
​
Viewing Spans in the Dashboard
All recorded spans are visible in the AgentOps dashboard:
Timeline View: Shows the sequence and duration of spans
Tree View: Displays the hierarchical relationship between spans
Details Panel: Provides in-depth information about each span
Analytics: Aggregates statistics across spans
​
Best Practices
Use descriptive names for spans to make them easily identifiable
Create a logical hierarchy with sessions, agents, and operations
Record relevant parameters and results for better debugging
Use consistent naming conventions for span types
Track costs and token usage to monitor resource consumption

Tags
Organize and filter your sessions with customizable tags

​
Adding Tags
You can add tags when initializing AgentOps, whicreh is the most common approach:
import agentops

# Initialize AgentOps with tags
agentops.init(
    api_key="YOUR_API_KEY",
    default_tags=["production", "customer-service", "gpt-4"]
)
Alternatively, when using manual trace creation:
# Initialize without auto-starting a session
agentops.init(api_key="YOUR_API_KEY", auto_start_session=False)

# Later start a trace with specific tags (modern approach)
trace = agentops.start_trace(trace_name="test_workflow", default_tags=["development", "testing", "claude-3"])
Legacy approach using agentops.start_session(default_tags=["development", "testing", "claude-3"]) is deprecated and will be removed in v4.0. Use agentops.start_trace() instead.
​
Tag Use Cases
Tags can be used for various purposes:
​
Environment Identification
Tag sessions based on their environment:
default_tags=["production"] # or ["development", "staging", "testing"]
​
Feature Tracking
Tag sessions related to specific features or components:
default_tags=["search-functionality", "user-authentication", "content-generation"]
​
User Segmentation
Tag sessions based on user characteristics:
default_tags=["premium-user", "new-user", "enterprise-customer"]
​
Experiment Tracking
Tag sessions as part of specific experiments:
default_tags=["experiment-123", "control-group", "variant-A"]
​
Model Identification
Tag sessions with the models being used:
default_tags=["gpt-4", "claude-3-opus", "mistral-large"]
​
Viewing Tagged Sessions
In the AgentOps dashboard:
Use the tag filter to select specific tags
Combine multiple tags to refine your view
Save filtered views for quick access
​
Best Practices
Use a consistent naming convention for tags
Include both broad categories and specific identifiers
Avoid using too many tags per session (3-5 is typically sufficient)
Consider using hierarchical tag structures (e.g., “env:production”, “model:gpt-4”)
Update your tagging strategy as your application evolves



from agentops.sdk.decorators import trace, agent, operation, tool
from openai import OpenAI
import agentops

agentops.init("your-api-key", auto_start_session=False)

@agent
class OrderProcessor:
    def __init__(self):
        print("🛒 OrderProcessor initialized")
    
    @tool(cost=0.01)
    def validate_payment(self, payment_info):
        """Payment validation service"""
        print(f"💳 Validating payment: {payment_info['card']}")
        result = {"valid": True, "transaction_id": "txn_123"}
        print(f"✅ Payment validation successful: {result['transaction_id']}")
        return result
    
    @tool(cost=0.02)
    def check_inventory(self, product_id, quantity):
        """Inventory check service"""
        print(f"📦 Checking inventory for {product_id} (qty: {quantity})")
        result = {"available": True, "reserved": quantity}
        print(f"✅ Inventory check complete: {quantity} units available")
        return result
    
    @operation
    def calculate_shipping(self, address, items):
        """Calculate shipping costs"""
        print(f"🚚 Calculating shipping to {address['city']}, {address['state']}")
        result = {"cost": 9.99, "method": "standard"}
        print(f"✅ Shipping calculated: ${result['cost']} ({result['method']})")
        return result
    
    @tool(cost=0.005)
    def send_confirmation_email(self, email, order_details):
        """Email service"""
        print(f"📧 Sending confirmation email to {email}")
        result = f"Confirmation sent to {email}"
        print(f"✅ Email sent successfully")
        return result

@trace(name="order-processing", tags=["ecommerce", "orders"])
def process_order(order_data):
    """Complete order processing workflow"""
    print(f"🚀 Starting order processing for {order_data['customer_email']}")
    print("=" * 60)
    
    processor = OrderProcessor()
    
    try:
        # Validate payment
        print("\n📋 Step 1: Payment Validation")
        payment_result = processor.validate_payment(order_data["payment"])
        if not payment_result["valid"]:
            print("❌ Payment validation failed!")
            return {"success": False, "error": "Payment validation failed"}
        
        # Check inventory for all items
        print("\n📋 Step 2: Inventory Check")
        for item in order_data["items"]:
            inventory_result = processor.check_inventory(
                item["product_id"], 
                item["quantity"]
            )
            if not inventory_result["available"]:
                print(f"❌ Item {item['product_id']} not available!")
                return {"success": False, "error": f"Item {item['product_id']} not available"}
        
        # Calculate shipping
        print("\n📋 Step 3: Shipping Calculation")
        shipping = processor.calculate_shipping(
            order_data["shipping_address"], 
            order_data["items"]
        )
        
        # Send confirmation
        print("\n📋 Step 4: Confirmation Email")
        confirmation = processor.send_confirmation_email(
            order_data["customer_email"],
            {
                "items": order_data["items"],
                "shipping": shipping,
                "payment": payment_result
            }
        )
        
        print("\n🎉 Order processing completed successfully!")
        print("=" * 60)
        
        return {
            "success": True,
            "order_id": "ORD_12345",
            "payment": payment_result,
            "shipping": shipping,
            "confirmation": confirmation
        }
        
    except Exception as e:
        print(f"💥 Order processing failed: {e}")
        return {"success": False, "error": str(e)}

# Usage
print("🎬 Running e-commerce order processing demo...")

order = {
    "customer_email": "customer@example.com",
    "payment": {"card": "****1234", "amount": 99.99},
    "items": [{"product_id": "PROD_001", "quantity": 2}],
    "shipping_address": {"city": "New York", "state": "NY"}
}

result = process_order(order)

print(f"\n📊 ORDER PROCESSING RESULT:")
print(f"   Success: {result['success']}")
if result['success']:
    print(f"   Order ID: {result['order_id']}")
    print(f"   Transaction: {result['payment']['transaction_id']}")
    print(f"   Shipping: ${result['shipping']['cost']}")
else:
    print(f"   Error: {result['error']}")
​


