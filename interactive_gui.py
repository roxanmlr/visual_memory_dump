"""
interactive_gui.py

Interactive Memory Simulator - A GUI for directly manipulating program memory.

This module provides an interactive interface where users can:
- Push and pop stack frames
- Allocate and free heap memory
- Create and modify variables
- See real-time visualization of memory state
- Undo/redo operations
- Save/load memory states

Usage:
    from interactive_gui import InteractiveMemorySimulator

    simulator = InteractiveMemorySimulator()
    simulator.run()
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog
from typing import List, Optional, Any
import json

from memory_model import (
    MemorySnapshot,
    SnapshotBuilder,
    GlobalStaticVariable,
    VariableStorageClass,
    PointerValue,
    create_initial_snapshot,
)
from memory_gui import MemoryRenderer, ColorScheme


# ============================================================
# Input Dialogs
# ============================================================

class VariableDialog(simpledialog.Dialog):
    """Dialog for entering variable information."""

    def __init__(self, parent, title, default_name="", default_type="int", default_value="0"):
        self.default_name = default_name
        self.default_type = default_type
        self.default_value = default_value
        self.result_data = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.name_entry = ttk.Entry(master, width=30)
        self.name_entry.insert(0, self.default_name)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(master, text="Type:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.type_entry = ttk.Entry(master, width=30)
        self.type_entry.insert(0, self.default_type)
        self.type_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(master, text="Value:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.value_entry = ttk.Entry(master, width=30)
        self.value_entry.insert(0, self.default_value)
        self.value_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(master, text="(Use 'null' for NULL pointer)").grid(
            row=3, column=0, columnspan=2, padx=5, pady=2
        )

        return self.name_entry

    def apply(self):
        name = self.name_entry.get().strip()
        type_name = self.type_entry.get().strip()
        value_str = self.value_entry.get().strip()

        if not name or not type_name:
            messagebox.showerror("Error", "Name and type are required")
            return

        # Parse value
        value = self._parse_value(value_str, type_name)

        self.result_data = {
            "name": name,
            "type": type_name,
            "value": value
        }

    def _parse_value(self, value_str: str, type_name: str) -> Any:
        """Parse value string into appropriate type."""
        value_str = value_str.strip()

        # Check for NULL pointer
        if value_str.lower() == "null":
            return PointerValue(0, type_name.replace("*", "").strip(), is_null=True)

        # Check for pointer (0x... or hex address)
        if "*" in type_name and value_str.startswith("0x"):
            try:
                addr = int(value_str, 16)
                target_type = type_name.replace("*", "").strip()
                return PointerValue(addr, target_type)
            except ValueError:
                pass

        # Try to parse as number
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # Return as string
        return value_str


class MallocDialog(simpledialog.Dialog):
    """Dialog for malloc operation."""

    def __init__(self, parent):
        self.result_data = None
        super().__init__(parent, "Allocate Heap Memory")

    def body(self, master):
        ttk.Label(master, text="Size (bytes):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.size_entry = ttk.Entry(master, width=30)
        self.size_entry.insert(0, "4")
        self.size_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(master, text="Type:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.type_entry = ttk.Entry(master, width=30)
        self.type_entry.insert(0, "int")
        self.type_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(master, text="Initial value:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.value_entry = ttk.Entry(master, width=30)
        self.value_entry.insert(0, "0")
        self.value_entry.grid(row=2, column=1, padx=5, pady=5)

        return self.size_entry

    def apply(self):
        try:
            size = int(self.size_entry.get())
            type_name = self.type_entry.get().strip()
            value_str = self.value_entry.get().strip()

            if size <= 0:
                messagebox.showerror("Error", "Size must be positive")
                return

            # Parse value
            try:
                value = int(value_str) if value_str else 0
            except ValueError:
                value = value_str

            self.result_data = {
                "size": size,
                "type": type_name,
                "value": value
            }
        except ValueError:
            messagebox.showerror("Error", "Invalid size")


# ============================================================
# Interactive Memory Simulator
# ============================================================

class InteractiveMemorySimulator:
    """Interactive GUI for memory manipulation."""

    def __init__(self):
        """Initialize the simulator."""
        self.root = tk.Tk()
        self.root.title("Interactive Memory Simulator")
        self.root.geometry("1400x900")

        # State management
        self.history: List[MemorySnapshot] = []
        self.current_index = -1

        # Color scheme
        self.colors = ColorScheme()

        # Create UI first (needed for renderer)
        self._create_ui()

        # Create and add initial snapshot
        initial = create_initial_snapshot(step_id=0, description="Initial state")
        self._add_snapshot(initial)

    def _create_ui(self):
        """Create the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Controls
        self._create_control_panel(main_frame)

        # Center - Canvas
        self._create_canvas_panel(main_frame)

        # Right panel - History and info
        self._create_info_panel(main_frame)

        # Bottom status bar
        self._create_status_bar()

    def _create_control_panel(self, parent):
        """Create the control panel with operation buttons."""
        control_frame = ttk.LabelFrame(parent, text="Memory Operations", width=280)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        control_frame.pack_propagate(False)

        # Scrollable frame for controls
        canvas = tk.Canvas(control_frame)
        scrollbar = ttk.Scrollbar(control_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Stack Operations
        stack_frame = ttk.LabelFrame(scrollable_frame, text="Stack Operations")
        stack_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            stack_frame,
            text="🔼 Push Frame",
            command=self.push_frame,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            stack_frame,
            text="🔽 Pop Frame",
            command=self.pop_frame,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            stack_frame,
            text="➕ Add Local Variable",
            command=self.add_local,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            stack_frame,
            text="➕ Add Parameter",
            command=self.add_parameter,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            stack_frame,
            text="✏️ Modify Variable",
            command=self.modify_variable,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        # Heap Operations
        heap_frame = ttk.LabelFrame(scrollable_frame, text="Heap Operations")
        heap_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            heap_frame,
            text="🆕 Malloc",
            command=self.malloc_memory,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            heap_frame,
            text="🗑️ Free",
            command=self.free_memory,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            heap_frame,
            text="✏️ Write to Heap",
            command=self.write_heap,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        # Global Operations
        global_frame = ttk.LabelFrame(scrollable_frame, text="Global Operations")
        global_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            global_frame,
            text="➕ Add Global",
            command=self.add_global,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            global_frame,
            text="✏️ Modify Global",
            command=self.modify_global,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        # History Operations
        history_frame = ttk.LabelFrame(scrollable_frame, text="History")
        history_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            history_frame,
            text="⬅️ Undo",
            command=self.undo,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            history_frame,
            text="➡️ Redo",
            command=self.redo,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            history_frame,
            text="🔄 Reset",
            command=self.reset,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        # File Operations
        file_frame = ttk.LabelFrame(scrollable_frame, text="File")
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            file_frame,
            text="💾 Save State",
            command=self.save_state,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            file_frame,
            text="📂 Load State",
            command=self.load_state,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            file_frame,
            text="📸 Export Image",
            command=self.export_image,
            width=25
        ).pack(fill=tk.X, padx=5, pady=2)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_canvas_panel(self, parent):
        """Create the canvas panel for visualization."""
        canvas_frame = ttk.LabelFrame(parent, text="Memory Visualization")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas with scrollbars
        self.canvas = tk.Canvas(
            canvas_frame,
            bg=self.colors.CANVAS_BG,
            scrollregion=(0, 0, 1200, 2000)
        )

        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create renderer
        self.renderer = MemoryRenderer(self.canvas, self.colors)

    def _create_info_panel(self, parent):
        """Create the info panel."""
        info_frame = ttk.Frame(parent, width=250)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        info_frame.pack_propagate(False)

        # Current state info
        state_frame = ttk.LabelFrame(info_frame, text="Current State")
        state_frame.pack(fill=tk.X, pady=(0, 5))

        self.state_text = scrolledtext.ScrolledText(
            state_frame,
            wrap=tk.WORD,
            width=30,
            height=12,
            font=("Courier", 9)
        )
        self.state_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # History list
        history_frame = ttk.LabelFrame(info_frame, text="History")
        history_frame.pack(fill=tk.BOTH, expand=True)

        self.history_listbox = tk.Listbox(history_frame, font=("Courier", 9))
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_listbox.bind("<<ListboxSelect>>", self._on_history_select)

    def _create_status_bar(self):
        """Create status bar."""
        self.status_label = ttk.Label(
            self.root,
            text="Ready - Click buttons to manipulate memory",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

    # ============================================================
    # Stack Operations
    # ============================================================

    def push_frame(self):
        """Push a new stack frame."""
        function_name = simpledialog.askstring(
            "Push Frame",
            "Enter function name:",
            initialvalue="main"
        )
        if not function_name:
            return

        try:
            current = self._current_snapshot()
            new_snapshot = (
                SnapshotBuilder(current)
                .push_frame(function_name)
                .set_step(
                    self.current_index + 1,
                    f"Pushed frame: {function_name}"
                )
                .build()
            )
            self._add_snapshot(new_snapshot)
            self.status_label.config(text=f"Pushed frame: {function_name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def pop_frame(self):
        """Pop the current stack frame."""
        try:
            current = self._current_snapshot()
            if not current.stack.frames:
                messagebox.showwarning("Warning", "Stack is empty")
                return

            frame_name = current.stack.frames[-1].function_name

            new_snapshot = (
                SnapshotBuilder(current)
                .pop_frame()
                .set_step(
                    self.current_index + 1,
                    f"Popped frame: {frame_name}"
                )
                .build()
            )
            self._add_snapshot(new_snapshot)
            self.status_label.config(text=f"Popped frame: {frame_name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_local(self):
        """Add a local variable to current frame."""
        current = self._current_snapshot()
        if not current.stack.frames:
            messagebox.showwarning("Warning", "No stack frame. Push a frame first.")
            return

        dialog = VariableDialog(self.root, "Add Local Variable")
        if dialog.result_data:
            try:
                data = dialog.result_data
                new_snapshot = (
                    SnapshotBuilder(current)
                    .set_local(data["name"], data["value"], data["type"])
                    .set_step(
                        self.current_index + 1,
                        f"Added local: {data['name']}"
                    )
                    .build()
                )
                self._add_snapshot(new_snapshot)
                self.status_label.config(text=f"Added local variable: {data['name']}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def add_parameter(self):
        """Add a parameter to current frame."""
        current = self._current_snapshot()
        if not current.stack.frames:
            messagebox.showwarning("Warning", "No stack frame. Push a frame first.")
            return

        dialog = VariableDialog(self.root, "Add Parameter")
        if dialog.result_data:
            try:
                data = dialog.result_data
                new_snapshot = (
                    SnapshotBuilder(current)
                    .set_parameter(data["name"], data["value"], data["type"])
                    .set_step(
                        self.current_index + 1,
                        f"Added parameter: {data['name']}"
                    )
                    .build()
                )
                self._add_snapshot(new_snapshot)
                self.status_label.config(text=f"Added parameter: {data['name']}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def modify_variable(self):
        """Modify a variable in current frame."""
        current = self._current_snapshot()
        if not current.stack.frames:
            messagebox.showwarning("Warning", "No stack frame")
            return

        frame = current.stack.frames[-1]
        all_vars = frame.all_variables()

        if not all_vars:
            messagebox.showwarning("Warning", "No variables in current frame")
            return

        # Ask which variable
        var_name = simpledialog.askstring(
            "Modify Variable",
            f"Enter variable name ({', '.join(all_vars.keys())}):"
        )
        if not var_name or var_name not in all_vars:
            return

        # Ask for new value
        old_value = all_vars[var_name].value
        value_str = simpledialog.askstring(
            "New Value",
            f"Current value: {old_value}\nEnter new value:",
            initialvalue=str(old_value)
        )
        if value_str is None:
            return

        try:
            # Parse value
            dialog = VariableDialog(self.root, "dummy")
            new_value = dialog._parse_value(value_str, all_vars[var_name].type_name)

            new_snapshot = (
                SnapshotBuilder(current)
                .update_local(var_name, new_value)
                .set_step(
                    self.current_index + 1,
                    f"Modified {var_name} = {new_value}"
                )
                .build()
            )
            self._add_snapshot(new_snapshot)
            self.status_label.config(text=f"Modified variable: {var_name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # Heap Operations
    # ============================================================

    def malloc_memory(self):
        """Allocate heap memory."""
        dialog = MallocDialog(self.root)
        if dialog.result_data:
            try:
                current = self._current_snapshot()
                data = dialog.result_data

                builder = SnapshotBuilder(current)
                builder, addr = builder.malloc(
                    data["size"],
                    data["type"],
                    data["value"]
                )

                new_snapshot = builder.set_step(
                    self.current_index + 1,
                    f"Malloc: {data['size']} bytes at {hex(addr)}"
                ).build()

                self._add_snapshot(new_snapshot)
                self.status_label.config(
                    text=f"Allocated {data['size']} bytes at {hex(addr)}"
                )
                messagebox.showinfo("Success", f"Allocated at address: {hex(addr)}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def free_memory(self):
        """Free heap memory."""
        current = self._current_snapshot()
        allocated = current.heap.get_all_allocated()

        if not allocated:
            messagebox.showwarning("Warning", "No allocated blocks")
            return

        # Show list of addresses
        addr_list = [hex(b.address) for b in allocated]
        addr_str = simpledialog.askstring(
            "Free Memory",
            f"Enter address to free:\n{', '.join(addr_list)}"
        )
        if not addr_str:
            return

        try:
            addr = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str)

            new_snapshot = (
                SnapshotBuilder(current)
                .free(addr)
                .set_step(
                    self.current_index + 1,
                    f"Freed memory at {hex(addr)}"
                )
                .build()
            )
            self._add_snapshot(new_snapshot)
            self.status_label.config(text=f"Freed memory at {hex(addr)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def write_heap(self):
        """Write to heap memory."""
        current = self._current_snapshot()
        allocated = current.heap.get_all_allocated()

        if not allocated:
            messagebox.showwarning("Warning", "No allocated blocks")
            return

        # Show list of addresses
        addr_list = [hex(b.address) for b in allocated]
        addr_str = simpledialog.askstring(
            "Write to Heap",
            f"Enter address:\n{', '.join(addr_list)}"
        )
        if not addr_str:
            return

        try:
            addr = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str)
            block = current.heap.get_block(addr)

            if not block:
                messagebox.showerror("Error", "Invalid address")
                return

            value_str = simpledialog.askstring(
                "New Value",
                f"Current value: {block.value}\nEnter new value:"
            )
            if value_str is None:
                return

            # Parse value
            dialog = VariableDialog(self.root, "dummy")
            new_value = dialog._parse_value(value_str, block.type_name)

            new_snapshot = (
                SnapshotBuilder(current)
                .write_heap(addr, new_value)
                .set_step(
                    self.current_index + 1,
                    f"Wrote to heap at {hex(addr)}"
                )
                .build()
            )
            self._add_snapshot(new_snapshot)
            self.status_label.config(text=f"Wrote to heap at {hex(addr)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # Global Operations
    # ============================================================

    def add_global(self):
        """Add a global variable."""
        dialog = VariableDialog(self.root, "Add Global Variable")
        if dialog.result_data:
            try:
                data = dialog.result_data
                current = self._current_snapshot()

                # Auto-generate address
                existing_addrs = [v.address for v in current.globals_statics.variables.values()]
                new_addr = 0x4000
                while new_addr in existing_addrs:
                    new_addr += 8

                global_var = GlobalStaticVariable(
                    name=data["name"],
                    address=new_addr,
                    value=data["value"],
                    type_name=data["type"],
                    storage_class=VariableStorageClass.GLOBAL,
                    section=".data"
                )

                new_snapshot = (
                    SnapshotBuilder(current)
                    .add_global(global_var)
                    .set_step(
                        self.current_index + 1,
                        f"Added global: {data['name']}"
                    )
                    .build()
                )
                self._add_snapshot(new_snapshot)
                self.status_label.config(text=f"Added global variable: {data['name']}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def modify_global(self):
        """Modify a global variable."""
        current = self._current_snapshot()
        globals_dict = current.globals_statics.variables

        if not globals_dict:
            messagebox.showwarning("Warning", "No global variables")
            return

        var_name = simpledialog.askstring(
            "Modify Global",
            f"Enter global name ({', '.join(globals_dict.keys())}):"
        )
        if not var_name or var_name not in globals_dict:
            return

        old_value = globals_dict[var_name].value
        value_str = simpledialog.askstring(
            "New Value",
            f"Current value: {old_value}\nEnter new value:",
            initialvalue=str(old_value)
        )
        if value_str is None:
            return

        try:
            # Parse value
            dialog = VariableDialog(self.root, "dummy")
            new_value = dialog._parse_value(value_str, globals_dict[var_name].type_name)

            new_snapshot = (
                SnapshotBuilder(current)
                .set_global(var_name, new_value)
                .set_step(
                    self.current_index + 1,
                    f"Modified global {var_name} = {new_value}"
                )
                .build()
            )
            self._add_snapshot(new_snapshot)
            self.status_label.config(text=f"Modified global: {var_name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # History Operations
    # ============================================================

    def undo(self):
        """Undo last operation."""
        if self.current_index > 0:
            self.current_index -= 1
            self.refresh_display()
            self.status_label.config(text="Undo")
        else:
            messagebox.showinfo("Info", "Nothing to undo")

    def redo(self):
        """Redo operation."""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            self.refresh_display()
            self.status_label.config(text="Redo")
        else:
            messagebox.showinfo("Info", "Nothing to redo")

    def reset(self):
        """Reset to initial state."""
        if messagebox.askyesno("Confirm", "Reset to initial state?"):
            self.history = [self.history[0]]
            self.current_index = 0
            self.refresh_display()
            self.status_label.config(text="Reset to initial state")

    # ============================================================
    # File Operations
    # ============================================================

    def save_state(self):
        """Save current state."""
        messagebox.showinfo("Info", "Save functionality - to be implemented")

    def load_state(self):
        """Load state."""
        messagebox.showinfo("Info", "Load functionality - to be implemented")

    def export_image(self):
        """Export to image."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".ps",
            filetypes=[("PostScript", "*.ps"), ("All Files", "*.*")]
        )
        if filename:
            try:
                bbox = self.canvas.bbox("all")
                if bbox:
                    self.canvas.postscript(
                        file=filename,
                        colormode="color",
                        x=bbox[0], y=bbox[1],
                        width=bbox[2] - bbox[0],
                        height=bbox[3] - bbox[1]
                    )
                    messagebox.showinfo("Success", f"Exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ============================================================
    # Helper Methods
    # ============================================================

    def _current_snapshot(self) -> MemorySnapshot:
        """Get current snapshot."""
        return self.history[self.current_index]

    def _add_snapshot(self, snapshot: MemorySnapshot):
        """Add snapshot to history."""
        # Remove any future history if we're not at the end
        self.history = self.history[:self.current_index + 1]

        # Add new snapshot
        self.history.append(snapshot)
        self.current_index = len(self.history) - 1

        # Refresh display
        self.refresh_display()

    def refresh_display(self):
        """Refresh the display."""
        current = self._current_snapshot()

        # Render visualization
        self.renderer.render_snapshot(current)

        # Update state info
        self._update_state_info(current)

        # Update history list
        self._update_history_list()

    def _update_state_info(self, snapshot: MemorySnapshot):
        """Update state information panel."""
        self.state_text.delete("1.0", tk.END)

        lines = []
        lines.append(f"Step: {snapshot.step_id}\n")
        lines.append(f"{snapshot.description or '(no description)'}\n")
        lines.append("\n")
        lines.append(f"Stack: {snapshot.stack.depth()} frame(s)\n")
        lines.append(f"Heap: {len(snapshot.heap.get_all_allocated())} block(s)\n")
        lines.append(f"      {snapshot.heap.total_allocated_size()} bytes\n")
        lines.append(f"Globals: {len(snapshot.globals_statics.variables)}\n")
        lines.append("\n")
        lines.append(f"History: {self.current_index + 1} / {len(self.history)}\n")

        self.state_text.insert("1.0", "".join(lines))

    def _update_history_list(self):
        """Update history listbox."""
        self.history_listbox.delete(0, tk.END)

        for i, snapshot in enumerate(self.history):
            prefix = "→ " if i == self.current_index else "  "
            text = f"{prefix}{i}: {snapshot.description or 'Step ' + str(snapshot.step_id)}"
            self.history_listbox.insert(tk.END, text)

        # Select current
        if self.current_index >= 0:
            self.history_listbox.selection_set(self.current_index)
            self.history_listbox.see(self.current_index)

    def _on_history_select(self, event):
        """Handle history selection."""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            if index != self.current_index:
                self.current_index = index
                self.refresh_display()

    def run(self):
        """Run the simulator."""
        self.root.mainloop()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    simulator = InteractiveMemorySimulator()
    simulator.run()
