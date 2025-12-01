# Interactive Memory Simulator - User Guide

## Overview

The Interactive Memory Simulator provides a hands-on GUI where you can directly manipulate program memory through buttons and dialogs, seeing real-time visualization of changes.

## Features

- ✨ **Direct Memory Manipulation**: Click buttons to perform operations
- 📊 **Real-time Visualization**: See memory state update instantly
- ⏮️ **Undo/Redo**: Full history with ability to go back/forward
- 💾 **State Management**: Save and load memory states
- 🎯 **Interactive Learning**: Perfect for learning C memory concepts

## Launching the Simulator

```bash
python interactive_gui.py
```

Or from Python:

```python
from interactive_gui import InteractiveMemorySimulator

simulator = InteractiveMemorySimulator()
simulator.run()
```

## GUI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Interactive Memory Simulator                                   │
├───────────┬─────────────────────────────────┬───────────────────┤
│           │                                 │                   │
│  Control  │   Memory Visualization          │  Current State    │
│  Panel    │   (Canvas)                      │  & History        │
│           │                                 │                   │
│  • Stack  │   ┌─────────┬─────────┬──────┐ │  Step: 5          │
│  • Heap   │   │ Globals │  Stack  │ Heap │ │  Stack: 2 frames  │
│  • Global │   │         │         │      │ │  Heap: 1 block    │
│  • History│   └─────────┴─────────┴──────┘ │                   │
│  • File   │                                 │  [History List]   │
│           │                                 │                   │
└───────────┴─────────────────────────────────┴───────────────────┘
│  Status: Ready - Click buttons to manipulate memory             │
└─────────────────────────────────────────────────────────────────┘
```

## Operations Guide

### Stack Operations

#### 🔼 Push Frame
Creates a new function call frame on the stack.

**Steps:**
1. Click "Push Frame"
2. Enter function name (e.g., "main", "foo")
3. Frame appears in the stack visualization

**Example:**
```
Click: Push Frame
Enter: main
Result: Empty main() frame added to stack
```

#### 🔽 Pop Frame
Removes the topmost stack frame (simulates function return).

**Steps:**
1. Click "Pop Frame"
2. Confirms removal
3. Frame disappears from stack

**Note:** Cannot pop from empty stack.

#### ➕ Add Local Variable
Adds a local variable to the current stack frame.

**Steps:**
1. Click "Add Local Variable"
2. Fill in dialog:
   - **Name**: Variable name (e.g., "x", "count")
   - **Type**: C type (e.g., "int", "char*", "float")
   - **Value**: Initial value
3. Variable appears in current frame

**Examples:**
```
Name: x        Type: int      Value: 10
Name: ptr      Type: int*     Value: 0x1000
Name: flag     Type: bool     Value: 1
Name: ptr      Type: void*    Value: null
```

**Special Values:**
- `null` → NULL pointer
- `0x1000` → Pointer to address 0x1000
- Numbers → Parsed as int/float
- Text → Stored as string

#### ➕ Add Parameter
Adds a function parameter to the current frame (similar to Add Local).

**Use this for:** Function arguments that were passed to the function.

#### ✏️ Modify Variable
Changes the value of an existing variable in the current frame.

**Steps:**
1. Click "Modify Variable"
2. Enter variable name from the list shown
3. Enter new value
4. Variable updates in visualization

### Heap Operations

#### 🆕 Malloc
Allocates memory on the heap.

**Steps:**
1. Click "Malloc"
2. Fill in dialog:
   - **Size**: Number of bytes (e.g., 4, 8, 16)
   - **Type**: What's being allocated (e.g., "int", "struct Node")
   - **Initial value**: Starting value
3. Block appears in heap visualization
4. **Important:** Note the address shown in the success message!

**Example:**
```
Size: 4        Type: int      Value: 0
→ Result: "Allocated at address: 0x1000"

Then you can create a pointer to it:
Name: ptr      Type: int*     Value: 0x1000
```

#### 🗑️ Free
Frees an allocated heap block.

**Steps:**
1. Click "Free"
2. List of allocated addresses shown
3. Enter address to free (e.g., "0x1000")
4. Block turns gray (freed) in visualization

**Note:** Address must exist and not already be freed (double-free prevented).

#### ✏️ Write to Heap
Modifies data in an allocated heap block.

**Steps:**
1. Click "Write to Heap"
2. Select address from list
3. Enter new value
4. Value updates in visualization

### Global Operations

#### ➕ Add Global
Creates a new global or static variable.

**Steps:**
1. Click "Add Global"
2. Fill in variable details
3. Address is auto-generated
4. Variable appears in globals section

**Example:**
```
Name: g_counter    Type: int       Value: 0
Name: g_flag       Type: bool      Value: 1
```

#### ✏️ Modify Global
Changes the value of an existing global variable.

**Steps:**
1. Click "Modify Global"
2. Select global from list
3. Enter new value

### History Operations

#### ⬅️ Undo
Go back one step in history. Restores previous memory state.

#### ➡️ Redo
Go forward one step (if you've undone operations).

#### 🔄 Reset
Clears all operations and returns to initial empty state.

**Confirmation required.**

### File Operations

#### 💾 Save State
Save the current memory state to a file (to be implemented).

#### 📂 Load State
Load a previously saved state (to be implemented).

#### 📸 Export Image
Export current visualization as PostScript image.

## Tutorial: Simulating a C Program

Let's simulate this C code:

```c
int g_count = 0;

int main() {
    int x = 10;
    int* ptr = malloc(sizeof(int));
    *ptr = 42;
    g_count++;
    free(ptr);
    return 0;
}
```

**Step-by-step:**

1. **Add global variable**
   - Click "Add Global"
   - Name: `g_count`, Type: `int`, Value: `0`

2. **Enter main()**
   - Click "Push Frame"
   - Function name: `main`

3. **Declare x**
   - Click "Add Local Variable"
   - Name: `x`, Type: `int`, Value: `10`

4. **Allocate memory**
   - Click "Malloc"
   - Size: `4`, Type: `int`, Value: `0`
   - **Note the address** (e.g., 0x1000)

5. **Create pointer**
   - Click "Add Local Variable"
   - Name: `ptr`, Type: `int*`, Value: `0x1000` (use address from step 4)

6. **Write to heap**
   - Click "Write to Heap"
   - Address: `0x1000`
   - Value: `42`

7. **Increment global**
   - Click "Modify Global"
   - Variable: `g_count`
   - Value: `1`

8. **Free memory**
   - Click "Free"
   - Address: `0x1000`

9. **Return from main**
   - Click "Pop Frame"

Now you can use Undo/Redo to step through the execution!

## Tips and Tricks

### Creating Pointers

To create a pointer to heap memory:
1. First allocate with Malloc (note the address)
2. Then create a variable with that address as the value

```
Malloc: Size 4, Type int → Gets address 0x1000
Add Local: Name ptr, Type int*, Value 0x1000
```

### NULL Pointers

Use the special value `null` or `NULL` when entering a pointer value:

```
Name: ptr      Type: int*     Value: null
```

### Linked Lists

To create a linked list:

```c
struct Node {
    int data;
    struct Node* next;
};
```

1. Malloc first node → get address 0x1000
2. Malloc second node → get address 0x2000
3. Write to first node: `{"data": 10, "next": "0x2000"}`
4. Write to second node: `{"data": 20, "next": "null"}`

### Viewing History

The history panel on the right shows all operations. Click any entry to jump to that state!

### Keyboard Shortcuts

- Click items in history list to jump to that state
- Use Undo/Redo buttons to navigate
- All operations are recorded for later review

## Common Errors and Solutions

### "No stack frame"
**Error:** Trying to add local/parameter without a frame.
**Solution:** Click "Push Frame" first.

### "Stack is empty"
**Error:** Trying to pop from empty stack.
**Solution:** Only pop if frames exist.

### "Invalid address"
**Error:** Trying to access non-existent heap address.
**Solution:** Use addresses returned by Malloc.

### "Variable not found"
**Error:** Trying to modify non-existent variable.
**Solution:** Check the list of available variables shown.

### "Double free"
**Error:** Trying to free already-freed memory.
**Solution:** Each address can only be freed once.

## Educational Use Cases

### 1. Teaching Stack Frames
- Push multiple frames to show call stack
- Add parameters and locals to each
- Pop frames to show returns

### 2. Demonstrating Heap Management
- Malloc several blocks
- Show fragmentation
- Demonstrate memory leaks (allocate without freeing)

### 3. Pointer Concepts
- Create pointers to stack variables
- Create pointers to heap
- Show NULL pointers
- Demonstrate dangling pointers (free then access)

### 4. Memory Errors
- Show stack overflow (many frames)
- Demonstrate memory leaks
- Show use-after-free (freed heap access)
- Demonstrate double-free

## Advanced Features

### History Navigation
- **Linear History**: Every operation is saved
- **Jump to Any Point**: Click in history list
- **Branching**: Make changes from any point in history

### Visual Feedback
- **Color Coding**: Different colors for stack/heap/globals
- **Gray Freed Blocks**: Freed heap blocks shown in gray
- **Address Display**: All addresses visible

## Limitations

- Addresses are auto-generated (can't choose specific addresses for stack/globals)
- No actual pointer arithmetic visualization
- Simplified type system
- No memory corruption simulation

## Future Enhancements

- Save/Load functionality
- Code editor to write C and simulate
- Automatic code execution
- Pointer arrows showing relationships
- Memory layout diagram
- Step-by-step debugging mode

## Troubleshooting

### GUI doesn't launch
Make sure tkinter is installed:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

### Operations not working
Check the status bar at the bottom for error messages.

### Can't see all memory
Use the scrollbars on the visualization panel.

## Summary

The Interactive Memory Simulator provides a hands-on way to learn and experiment with C memory management. Click buttons to perform operations, see instant visual feedback, and use undo/redo to explore different scenarios.

Perfect for:
- Learning C memory concepts
- Teaching programming classes
- Demonstrating memory bugs
- Experimenting with pointer operations
- Understanding stack/heap interaction
