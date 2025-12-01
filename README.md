# Visual Memory Dump

A Python library for modeling and visualizing the memory state of C programs. This library provides a rich set of tools for creating snapshots of program memory including stack frames, heap allocations, global variables, and CPU state.

## Features

- 📊 **Complete Memory Model**: Model stack, heap, globals/statics, and CPU state
- 🏗️ **Immutable Snapshots**: Create memory snapshots with full state preservation
- 🔨 **Builder Pattern**: Fluent API for constructing memory states
- 🎨 **Console Rendering**: Built-in console visualization with customizable output
- 🖼️ **Graphical UI**: Interactive GUI for visualizing memory states (tkinter-based)
- 🔍 **Memory Analysis**: Find pointers, detect leaks, and track allocations
- 📝 **Type System**: Support for structs, unions, and typedefs
- 🧪 **Comprehensive Tests**: Extensive test coverage

## Installation

```bash
# Clone the repository
git clone https://github.com/roxanmlr/visual_memory_dump.git
cd visual_memory_dump

# Install dependencies (for testing)
pip install pytest

# For GUI support (optional)
# tkinter usually comes with Python, but on some Linux systems:
# Ubuntu/Debian: sudo apt-get install python3-tk
# Fedora: sudo dnf install python3-tkinter
# macOS/Windows: tkinter is included with Python
```

## Quick Start

```python
from memory_model import (
    create_initial_snapshot,
    SnapshotBuilder,
    GlobalStaticVariable,
    VariableStorageClass,
    PointerValue,
)

# Create initial state with a global variable
g = GlobalStaticVariable(
    name="counter",
    address=0x4040,
    value=0,
    type_name="int",
    storage_class=VariableStorageClass.GLOBAL,
    section=".data",
)

snapshot0 = create_initial_snapshot(globals=[g])
snapshot0.print()

# Create next state: enter main() and declare local variable
snapshot1 = (
    SnapshotBuilder(snapshot0)
    .push_frame("main")
    .set_local("x", 10, "int")
    .set_step(1, "After int x = 10")
    .build()
)
snapshot1.print()
```

## Core Concepts

### Memory Snapshots

A `MemorySnapshot` represents the complete state of program memory at a specific point in time:

```python
snapshot = MemorySnapshot(
    step_id=0,
    description="Initial state",
    globals_statics=GlobalStaticSegment(),
    heap=HeapSegment(),
    stack=StackSegment(),
    types=TypeRegistry(),
    cpu=CpuState(),
)
```

### Snapshot Builder

The `SnapshotBuilder` provides a fluent API for creating new snapshots from existing ones:

```python
builder = SnapshotBuilder(snapshot0)
new_snapshot = (
    builder
    .push_frame("main")
    .set_local("x", 10, "int")
    .malloc(4, "int", 0)
    .set_step(1, "Description")
    .build()
)
```

### Memory Segments

#### Stack Segment

Models the call stack with frames, local variables, and parameters:

```python
# Push a new stack frame
builder.push_frame("foo", return_address=0x400100)

# Add function parameter
builder.set_parameter("arg", 5, "int")

# Add local variable
builder.set_local("result", 10, "int")

# Update existing local
builder.update_local("result", 20)

# Pop frame when returning
builder.pop_frame()
```

#### Heap Segment

Models dynamic memory allocation:

```python
# Allocate memory
builder, addr = builder.malloc(
    size=4,
    type_name="int",
    initial_value=0,
    allocation_site="main:42"
)

# Write to heap
builder.write_heap(addr, 100)

# Read from heap
value = builder.read_heap(addr)

# Free memory
builder.free(addr)
```

#### Global/Static Segment

Models global and static variables:

```python
g = GlobalStaticVariable(
    name="counter",
    address=0x4000,
    value=0,
    type_name="int",
    storage_class=VariableStorageClass.GLOBAL,
    section=".data",
)

# Update global
builder.set_global("counter", 42)

# Add new global
builder.add_global(new_global_var)
```

### Type System

Register custom types (structs, unions, typedefs):

```python
from memory_model import TypeRegistry, StructDescriptor, FieldDescriptor

# Create type registry
types = TypeRegistry()

# Register struct
point_struct = StructDescriptor(
    name="Point",
    fields=[
        FieldDescriptor("x", "int", 0),
        FieldDescriptor("y", "int", 4),
    ],
    size=8,
)
types.register_struct(point_struct)

# Register typedef
types.register_typedef("MyInt", "int")

# Resolve type through typedef chain
types.resolve_type("MyInt")  # Returns "int"
```

### Pointers

Model pointer values:

```python
# Create pointer to heap address
ptr = PointerValue(0x1000, "int")

# NULL pointer
null_ptr = PointerValue(0, "void", is_null=True)

# Store pointer in variable
builder.set_local("ptr", ptr, "int*")
```

## Complete Example: Simulating a C Program

Let's simulate this C program:

```c
int g_counter = 0;

int main() {
    int x = 10;
    int* ptr = malloc(sizeof(int));
    *ptr = 42;
    g_counter++;
    free(ptr);
    return 0;
}
```

Here's how to model it:

```python
from memory_model import *

# Step 0: Initial state
g = GlobalStaticVariable(
    name="g_counter",
    address=0x4000,
    value=0,
    type_name="int",
    storage_class=VariableStorageClass.GLOBAL,
    section=".data",
)
snapshot0 = create_initial_snapshot(globals=[g], description="Program start")

# Step 1: Enter main()
snapshot1 = (
    SnapshotBuilder(snapshot0)
    .push_frame("main")
    .set_step(1, "Entered main()")
    .build()
)

# Step 2: int x = 10
snapshot2 = (
    SnapshotBuilder(snapshot1)
    .set_local("x", 10, "int")
    .set_step(2, "int x = 10")
    .build()
)

# Step 3: int* ptr = malloc(sizeof(int))
builder3 = SnapshotBuilder(snapshot2)
builder3, heap_addr = builder3.malloc(4, "int", 0, allocation_site="main:4")
snapshot3 = (
    builder3
    .set_local("ptr", PointerValue(heap_addr, "int"), "int*")
    .set_step(3, "Allocated heap memory")
    .build()
)

# Step 4: *ptr = 42
snapshot4 = (
    SnapshotBuilder(snapshot3)
    .write_heap(heap_addr, 42)
    .set_step(4, "*ptr = 42")
    .build()
)

# Step 5: g_counter++
snapshot5 = (
    SnapshotBuilder(snapshot4)
    .set_global("g_counter", 1)
    .set_step(5, "g_counter++")
    .build()
)

# Step 6: free(ptr)
snapshot6 = (
    SnapshotBuilder(snapshot5)
    .free(heap_addr)
    .set_step(6, "free(ptr)")
    .build()
)

# Step 7: return 0
snapshot7 = (
    SnapshotBuilder(snapshot6)
    .pop_frame()
    .set_step(7, "return 0")
    .build()
)

# Print each step
for snapshot in [snapshot0, snapshot1, snapshot2, snapshot3, snapshot4, snapshot5, snapshot6, snapshot7]:
    snapshot.print()
    print("\n")
```

## Memory Analysis

### Finding Pointers

Find all pointers that point to a specific address:

```python
# Find all pointers to heap address
pointers = snapshot.find_all_pointers_to(heap_addr)
for desc, addr in pointers:
    print(f"Pointer at {desc} -> {hex(addr)}")
```

### Memory Leak Detection

Detect unreachable heap allocations:

```python
# Define reachable addresses (from stack/global pointers)
reachable = {0x1000, 0x2000}

# Find leaked blocks
leaks = snapshot.heap.find_leaks(reachable)
for leak in leaks:
    print(f"Leaked block: {hex(leak.address)} ({leak.size} bytes)")
```

### Snapshot Diffing

Compare two snapshots to see what changed:

```python
from memory_model import diff_snapshots

diff = diff_snapshots(snapshot0, snapshot1)
print(diff)
```

Output:
```
=== Changes from Step 0 to Step 1 ===

Stack:
  + Pushed frame: main

(other changes...)
```

## Graphical User Interface

The library includes two GUI options:

### 1. Visualization GUI (View Mode)
For viewing pre-created snapshot sequences.

### 2. Interactive Simulator (Edit Mode) ⭐ NEW
**Directly manipulate memory through GUI buttons!**

## Interactive Memory Simulator

The Interactive Simulator lets you perform memory operations through GUI buttons and see real-time updates.

### Quick Start

```bash
python interactive_gui.py
```

### Available Operations

**Stack:**
- 🔼 Push Frame - Add function call
- 🔽 Pop Frame - Return from function
- ➕ Add Local/Parameter - Create variables
- ✏️ Modify Variable - Change values

**Heap:**
- 🆕 Malloc - Allocate memory
- 🗑️ Free - Deallocate memory
- ✏️ Write to Heap - Modify heap data

**Globals:**
- ➕ Add Global - Create global variable
- ✏️ Modify Global - Change global value

**History:**
- ⬅️ Undo / ➡️ Redo - Navigate operations
- 🔄 Reset - Start over
- Click history items to jump to any state

### Interactive Tutorial

Simulate `int x = 10; int* ptr = malloc(4);`:

1. Click "Push Frame" → Enter "main"
2. Click "Add Local" → Name: x, Type: int, Value: 10
3. Click "Malloc" → Size: 4, Type: int → Note address
4. Click "Add Local" → Name: ptr, Type: int*, Value: 0x1000

See [INTERACTIVE_GUI.md](INTERACTIVE_GUI.md) for complete guide.

## Visualization GUI (Snapshot Viewer)

For viewing pre-created snapshot sequences:

### Launching the Visualization GUI

```python
from memory_gui import visualize_snapshots

# Create your snapshots
snapshots = [snapshot0, snapshot1, snapshot2, ...]

# Launch the GUI
visualize_snapshots(snapshots)
```

### GUI Features

- **Step Navigation**: Navigate through snapshots using buttons, keyboard, or slider
- **Interactive Details**: Click on memory items to see detailed information
- **Color-Coded Visualization**:
  - Stack frames in blue
  - Heap blocks in purple (freed blocks in gray)
  - Global variables in green
  - CPU registers in yellow
- **Memory Layout**: Visual representation of stack, heap, and global segments
- **Export**: Save visualizations as PostScript files
- **Real-time Updates**: See memory state changes step-by-step

### GUI Demo

Run the included demo:

```bash
python gui_demo.py
```

This demo simulates a C program with:
- Global variables
- Linked list allocation on heap
- Function calls with parameters
- Pointer manipulation
- Memory freeing

### GUI Controls

- **First/Last**: Jump to first or last snapshot
- **Previous/Next**: Navigate one step at a time
- **Slider**: Jump to any step quickly
- **Click**: Click on memory items for details
- **Export**: Save current view as image

### Screenshot Description

The GUI displays three columns:
1. **Left**: Global/Static variables and CPU state
2. **Center**: Stack frames with parameters and locals
3. **Right**: Heap allocations

Each memory item shows:
- Variable/block name
- Type information
- Memory address
- Current value

### MemoryVisualizer Class

For more control, use the `MemoryVisualizer` class directly:

```python
from memory_gui import MemoryVisualizer

visualizer = MemoryVisualizer(snapshots)

# Customize if needed
visualizer.colors.STACK_BG = "#YOUR_COLOR"

# Run
visualizer.run()
```

## Configuration

Customize console rendering:

```python
from memory_model import render_config

# Use ASCII arrows instead of Unicode
render_config.pointer_arrow = "->"

# Show addresses in decimal
render_config.show_addresses_hex = False

# Compact output mode
render_config.compact_mode = True

# Hide frame pointers
render_config.show_frame_pointers = False
```

## Advanced Features

### CPU State

Track CPU registers:

```python
snapshot = (
    SnapshotBuilder(base)
    .set_pc(0x400000)      # Program counter
    .set_sp(0x7fff0000)    # Stack pointer
    .set_bp(0x7fff0010)    # Base pointer
    .build()
)
```

### Nested Function Calls

Model complex call stacks:

```python
# main() calls foo() calls bar()
snapshot = (
    SnapshotBuilder(base)
    .push_frame("main")
    .set_local("a", 5, "int")
    .push_frame("foo")
    .set_parameter("x", 5, "int")
    .set_local("b", 10, "int")
    .push_frame("bar")
    .set_parameter("y", 10, "int")
    .build()
)

# Stack depth is 3
assert snapshot.stack.depth() == 3

# Current frame is bar
assert snapshot.stack.current_frame().function_name == "bar"
```

### Value Lookup by Address

Look up any value by its address:

```python
value = snapshot.get_value_at_address(0x7fff0000)
if value is not None:
    print(f"Value at address: {value}")
```

## API Reference

### Classes

#### `MemorySnapshot`
- Complete memory state at a point in time
- Methods: `to_console()`, `print()`, `get_value_at_address()`, `find_all_pointers_to()`

#### `SnapshotBuilder`
- Builder for creating snapshots
- Stack methods: `push_frame()`, `pop_frame()`, `set_local()`, `set_parameter()`, `update_local()`
- Heap methods: `malloc()`, `free()`, `write_heap()`, `read_heap()`
- Global methods: `set_global()`, `add_global()`
- CPU methods: `set_pc()`, `set_sp()`, `set_bp()`
- Build: `build()`, `set_step()`

#### `GlobalStaticSegment`
- Global and static variables
- Methods: `get_variable()`, `get_by_address()`

#### `HeapSegment`
- Heap allocations
- Methods: `get_block()`, `get_all_allocated()`, `get_all_freed()`, `total_allocated_size()`, `find_leaks()`

#### `StackSegment`
- Call stack
- Methods: `current_frame()`, `find_variable()`, `depth()`

#### `StackFrame`
- Single stack frame
- Methods: `get_variable()`, `all_variables()`

#### `TypeRegistry`
- Type definitions
- Methods: `register_struct()`, `register_union()`, `register_typedef()`, `resolve_type()`

### Functions

#### `create_initial_snapshot()`
Create an initial memory snapshot.

**Parameters:**
- `globals`: List of global/static variables (optional)
- `types`: Type registry (optional)
- `cpu`: CPU state (optional)
- `step_id`: Step identifier (default: 0)
- `description`: Description (default: "Initial state")

#### `diff_snapshots(old, new)`
Generate a diff between two snapshots.

**Parameters:**
- `old`: Earlier snapshot
- `new`: Later snapshot

**Returns:** String describing changes

## Testing

Run the test suite:

```bash
# Run all tests
pytest test_memory_model.py -v

# Run specific test class
pytest test_memory_model.py::TestSnapshotBuilder -v

# Run with coverage
pytest test_memory_model.py --cov=memory_model --cov-report=html
```

## Error Handling

The library provides clear error messages for common mistakes:

```python
# RuntimeError: No frame on stack
builder.set_local("x", 10, "int")  # Without push_frame()

# KeyError: Block not found
builder.free(0x9999)  # Non-existent address

# ValueError: Double free
builder.free(addr)
builder.free(addr)  # Error!

# ValueError: Already allocated
builder.malloc(4, "int", 0, address=0x1000)
builder.malloc(4, "int", 0, address=0x1000)  # Error!
```

## Best Practices

1. **Use Descriptive Step Descriptions**: Make it clear what each snapshot represents
   ```python
   .set_step(5, "After loop iteration i=3")
   ```

2. **Track Allocation Sites**: Include source locations for heap allocations
   ```python
   builder.malloc(4, "int", 0, allocation_site="foo.c:42")
   ```

3. **Check for Memory Leaks**: Use `find_leaks()` to detect unreachable allocations

4. **Use Type Registry**: Define your structs for better documentation
   ```python
   types = TypeRegistry()
   types.register_struct(my_struct)
   snapshot = create_initial_snapshot(types=types)
   ```

5. **Chain Builder Calls**: Use fluent API for cleaner code
   ```python
   snapshot = (
       SnapshotBuilder(base)
       .push_frame("main")
       .set_local("x", 10, "int")
       .build()
   )
   ```

## Use Cases

- **Education**: Teach memory management concepts in C
- **Debugging**: Visualize memory state during debugging
- **Documentation**: Create visual examples for technical documentation
- **Testing**: Verify memory behavior in test suites
- **Analysis**: Analyze program memory patterns and detect issues

## Contributing

Contributions are welcome! Please ensure:
- All tests pass: `pytest test_memory_model.py`
- Code is documented with docstrings
- New features include tests
- Follow the existing code style

## License

[Add your license here]

## Authors

Roxan MLR

## Acknowledgments

Built with Python's dataclasses and type hints for clean, maintainable code.
