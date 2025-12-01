"""
memory_gui.py

Graphical User Interface for visualizing memory snapshots from the memory_model library.

This module provides a tkinter-based GUI for:
- Visualizing stack, heap, and global memory segments
- Navigating through memory snapshots step-by-step
- Showing pointer relationships with arrows
- Highlighting memory regions
- Exporting visualizations

Usage:
    from memory_gui import MemoryVisualizer

    # Create snapshots
    snapshots = [snapshot0, snapshot1, snapshot2, ...]

    # Launch GUI
    visualizer = MemoryVisualizer(snapshots)
    visualizer.run()
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from typing import List, Optional, Tuple, Dict, Any
import math

from memory_model import (
    MemorySnapshot,
    PointerValue,
    HeapBlock,
    StackFrame,
    GlobalStaticVariable,
)


# ============================================================
# Color Scheme
# ============================================================

class ColorScheme:
    """Color scheme for memory visualization."""

    # Memory regions
    STACK_BG = "#E3F2FD"           # Light blue
    STACK_FRAME = "#90CAF9"         # Blue
    STACK_PARAM = "#64B5F6"         # Darker blue

    HEAP_BG = "#F3E5F5"             # Light purple
    HEAP_ALLOCATED = "#CE93D8"      # Purple
    HEAP_FREED = "#BDBDBD"          # Gray

    GLOBAL_BG = "#E8F5E9"           # Light green
    GLOBAL_VAR = "#81C784"          # Green

    # UI elements
    POINTER_ARROW = "#FF6B6B"       # Red
    HIGHLIGHT = "#FFD54F"           # Yellow
    TEXT = "#212121"                # Dark gray
    BORDER = "#757575"              # Gray
    CANVAS_BG = "#FAFAFA"           # Very light gray

    # CPU
    CPU_BG = "#FFF9C4"              # Light yellow
    CPU_REG = "#FFF59D"             # Yellow


# ============================================================
# Memory Renderer
# ============================================================

class MemoryRenderer:
    """Renders memory snapshots onto a tkinter canvas."""

    def __init__(self, canvas: tk.Canvas, colors: ColorScheme):
        """Initialize renderer.

        Args:
            canvas: tkinter Canvas to draw on
            colors: Color scheme to use
        """
        self.canvas = canvas
        self.colors = colors
        self.scale = 1.0
        self.offset_x = 20
        self.offset_y = 20

        # Layout configuration
        self.region_width = 300
        self.region_spacing = 40
        self.item_height = 30
        self.item_spacing = 5

        # Keep track of drawn items for interaction
        self.item_map: Dict[int, Tuple[str, Any]] = {}  # canvas_id -> (type, object)

        # Keep track of item positions for pointer arrows
        # address -> (x, y, width, height) bounding box
        self.item_positions: Dict[int, Tuple[int, int, int, int]] = {}

    def clear(self) -> None:
        """Clear the canvas."""
        self.canvas.delete("all")
        self.item_map.clear()
        self.item_positions.clear()

    def render_snapshot(self, snapshot: MemorySnapshot) -> None:
        """Render a complete memory snapshot.

        Args:
            snapshot: The snapshot to render
        """
        self.clear()

        y_offset = self.offset_y

        # Render title
        title = f"Step {snapshot.step_id}"
        if snapshot.description:
            title += f": {snapshot.description}"
        self.canvas.create_text(
            self.offset_x + 10,
            y_offset,
            text=title,
            font=("Arial", 14, "bold"),
            anchor="nw",
            fill=self.colors.TEXT,
        )
        y_offset += 40

        # Calculate layout positions
        col1_x = self.offset_x
        col2_x = col1_x + self.region_width + self.region_spacing
        col3_x = col2_x + self.region_width + self.region_spacing

        # Render globals (column 1)
        globals_height = self._render_globals(
            snapshot.globals_statics.variables,
            col1_x,
            y_offset
        )

        # Render stack (column 2)
        stack_height = self._render_stack(
            snapshot.stack.frames,
            col2_x,
            y_offset
        )

        # Render heap (column 3)
        heap_height = self._render_heap(
            snapshot.heap.blocks,
            col3_x,
            y_offset
        )

        # Render CPU state below globals if present
        if snapshot.cpu is not None:
            self._render_cpu(snapshot.cpu, col1_x, y_offset + globals_height + 20)

        # Draw pointers after everything else so they're on top
        self._render_pointers(snapshot)

        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_globals(
        self,
        variables: Dict[str, GlobalStaticVariable],
        x: int,
        y: int
    ) -> int:
        """Render global/static variables.

        Returns:
            Height of the rendered section
        """
        start_y = y

        # Header
        header_id = self.canvas.create_rectangle(
            x, y,
            x + self.region_width, y + 30,
            fill=self.colors.GLOBAL_BG,
            outline=self.colors.BORDER,
            width=2,
        )
        text_id = self.canvas.create_text(
            x + 10, y + 15,
            text="Global & Static Variables",
            font=("Arial", 11, "bold"),
            anchor="w",
            fill=self.colors.TEXT,
        )
        y += 35

        if not variables:
            empty_id = self.canvas.create_text(
                x + self.region_width // 2, y + 15,
                text="(no variables)",
                font=("Arial", 9, "italic"),
                fill=self.colors.BORDER,
            )
            y += 30
        else:
            for var in variables.values():
                var_height = self._render_variable_box(
                    x, y,
                    var.name,
                    var.value,
                    var.type_name,
                    var.address,
                    self.colors.GLOBAL_VAR,
                    ("global", var)
                )
                y += var_height + self.item_spacing

        return y - start_y

    def _render_stack(self, frames: List[StackFrame], x: int, y: int) -> int:
        """Render stack frames.

        Returns:
            Height of the rendered section
        """
        start_y = y

        # Header
        header_id = self.canvas.create_rectangle(
            x, y,
            x + self.region_width, y + 30,
            fill=self.colors.STACK_BG,
            outline=self.colors.BORDER,
            width=2,
        )
        text_id = self.canvas.create_text(
            x + 10, y + 15,
            text=f"Stack ({len(frames)} frame(s))",
            font=("Arial", 11, "bold"),
            anchor="w",
            fill=self.colors.TEXT,
        )
        y += 35

        if not frames:
            empty_id = self.canvas.create_text(
                x + self.region_width // 2, y + 15,
                text="(empty stack)",
                font=("Arial", 9, "italic"),
                fill=self.colors.BORDER,
            )
            y += 30
        else:
            for frame in frames:
                frame_height = self._render_stack_frame(x, y, frame)
                y += frame_height + self.item_spacing

        return y - start_y

    def _render_stack_frame(self, x: int, y: int, frame: StackFrame) -> int:
        """Render a single stack frame.

        Returns:
            Height of the rendered frame
        """
        start_y = y

        # Frame header
        frame_id = self.canvas.create_rectangle(
            x, y,
            x + self.region_width, y + 25,
            fill=self.colors.STACK_FRAME,
            outline=self.colors.BORDER,
            width=1,
        )
        self.item_map[frame_id] = ("frame", frame)

        text_id = self.canvas.create_text(
            x + 10, y + 12,
            text=f"Frame: {frame.function_name}",
            font=("Arial", 10, "bold"),
            anchor="w",
            fill=self.colors.TEXT,
        )
        y += 30

        # Parameters
        if frame.parameters:
            param_label = self.canvas.create_text(
                x + 10, y,
                text="Parameters:",
                font=("Arial", 9, "italic"),
                anchor="nw",
                fill=self.colors.TEXT,
            )
            y += 15

            for var in frame.parameters.values():
                var_height = self._render_variable_box(
                    x + 10, y,
                    var.name,
                    var.value,
                    var.type_name,
                    var.address,
                    self.colors.STACK_PARAM,
                    ("param", var),
                    width=self.region_width - 20
                )
                y += var_height + self.item_spacing

        # Locals
        if frame.locals:
            local_label = self.canvas.create_text(
                x + 10, y,
                text="Locals:",
                font=("Arial", 9, "italic"),
                anchor="nw",
                fill=self.colors.TEXT,
            )
            y += 15

            for var in frame.locals.values():
                var_height = self._render_variable_box(
                    x + 10, y,
                    var.name,
                    var.value,
                    var.type_name,
                    var.address,
                    self.colors.STACK_FRAME,
                    ("local", var),
                    width=self.region_width - 20
                )
                y += var_height + self.item_spacing

        if not frame.parameters and not frame.locals:
            empty_id = self.canvas.create_text(
                x + self.region_width // 2, y,
                text="(no variables)",
                font=("Arial", 8, "italic"),
                fill=self.colors.BORDER,
            )
            y += 20

        return y - start_y

    def _render_heap(self, blocks: Dict[int, HeapBlock], x: int, y: int) -> int:
        """Render heap blocks.

        Returns:
            Height of the rendered section
        """
        start_y = y

        # Count allocated blocks
        allocated = [b for b in blocks.values() if not b.is_freed]

        # Header
        header_id = self.canvas.create_rectangle(
            x, y,
            x + self.region_width, y + 30,
            fill=self.colors.HEAP_BG,
            outline=self.colors.BORDER,
            width=2,
        )
        text_id = self.canvas.create_text(
            x + 10, y + 15,
            text=f"Heap ({len(allocated)} allocated)",
            font=("Arial", 11, "bold"),
            anchor="w",
            fill=self.colors.TEXT,
        )
        y += 35

        if not blocks:
            empty_id = self.canvas.create_text(
                x + self.region_width // 2, y + 15,
                text="(no allocations)",
                font=("Arial", 9, "italic"),
                fill=self.colors.BORDER,
            )
            y += 30
        else:
            # Sort by address
            sorted_blocks = sorted(blocks.values(), key=lambda b: b.address)
            for block in sorted_blocks:
                block_height = self._render_heap_block(x, y, block)
                y += block_height + self.item_spacing

        return y - start_y

    def _render_heap_block(self, x: int, y: int, block: HeapBlock) -> int:
        """Render a heap block.

        Returns:
            Height of the rendered block
        """
        color = self.colors.HEAP_FREED if block.is_freed else self.colors.HEAP_ALLOCATED

        # Block rectangle
        block_id = self.canvas.create_rectangle(
            x, y,
            x + self.region_width, y + self.item_height,
            fill=color,
            outline=self.colors.BORDER,
            width=1,
        )
        self.item_map[block_id] = ("heap", block)

        # Address
        addr_text = hex(block.address)
        addr_id = self.canvas.create_text(
            x + 5, y + 5,
            text=addr_text,
            font=("Courier", 8),
            anchor="nw",
            fill=self.colors.TEXT,
        )

        # Type and size
        type_text = f"{block.type_name} ({block.size}B)"
        type_id = self.canvas.create_text(
            x + 5, y + 18,
            text=type_text,
            font=("Arial", 8),
            anchor="nw",
            fill=self.colors.TEXT,
        )

        # Value
        if block.is_freed:
            val_text = "FREED"
        else:
            val_text = self._format_value(block.value)

        val_id = self.canvas.create_text(
            x + self.region_width - 5, y + 15,
            text=val_text,
            font=("Arial", 9, "bold"),
            anchor="ne",
            fill=self.colors.TEXT,
        )

        # Track position for pointer arrows
        self.item_positions[block.address] = (x, y, self.region_width, self.item_height)

        return self.item_height

    def _render_cpu(self, cpu, x: int, y: int) -> int:
        """Render CPU state.

        Returns:
            Height of the rendered section
        """
        start_y = y

        # Header
        header_id = self.canvas.create_rectangle(
            x, y,
            x + self.region_width, y + 25,
            fill=self.colors.CPU_BG,
            outline=self.colors.BORDER,
            width=2,
        )
        text_id = self.canvas.create_text(
            x + 10, y + 12,
            text="CPU State",
            font=("Arial", 11, "bold"),
            anchor="w",
            fill=self.colors.TEXT,
        )
        y += 30

        registers = [
            ("PC", cpu.pc),
            ("SP", cpu.sp),
            ("BP", cpu.bp),
        ]

        for name, value in registers:
            if value is not None:
                reg_id = self.canvas.create_rectangle(
                    x + 5, y,
                    x + self.region_width - 5, y + 20,
                    fill=self.colors.CPU_REG,
                    outline=self.colors.BORDER,
                )
                text_id = self.canvas.create_text(
                    x + 10, y + 10,
                    text=f"{name}: {hex(value)}",
                    font=("Courier", 9),
                    anchor="w",
                    fill=self.colors.TEXT,
                )
                y += 25

        return y - start_y

    def _render_variable_box(
        self,
        x: int,
        y: int,
        name: str,
        value: Any,
        type_name: str,
        address: int,
        color: str,
        item_data: Tuple[str, Any],
        width: Optional[int] = None
    ) -> int:
        """Render a variable box.

        Returns:
            Height of the rendered box
        """
        box_width = width if width is not None else self.region_width

        # Box
        box_id = self.canvas.create_rectangle(
            x, y,
            x + box_width, y + self.item_height,
            fill=color,
            outline=self.colors.BORDER,
            width=1,
        )
        self.item_map[box_id] = item_data

        # Name and type
        name_text = f"{name}: {type_name}"
        name_id = self.canvas.create_text(
            x + 5, y + 5,
            text=name_text,
            font=("Arial", 9, "bold"),
            anchor="nw",
            fill=self.colors.TEXT,
        )

        # Value
        val_text = self._format_value(value)
        val_id = self.canvas.create_text(
            x + 5, y + 18,
            text=f"= {val_text}",
            font=("Arial", 8),
            anchor="nw",
            fill=self.colors.TEXT,
        )

        # Address
        addr_text = hex(address)
        addr_id = self.canvas.create_text(
            x + box_width - 5, y + 15,
            text=addr_text,
            font=("Courier", 7),
            anchor="ne",
            fill=self.colors.BORDER,
        )

        # Track position for pointer arrows
        self.item_positions[address] = (x, y, box_width, self.item_height)

        return self.item_height

    def _render_pointers(self, snapshot: MemorySnapshot) -> None:
        """Render pointer arrows connecting memory locations."""
        # Collect all pointers: (source_address, target_address, pointer_value)
        pointers: List[Tuple[int, int, PointerValue]] = []

        # Check globals
        for var in snapshot.globals_statics.variables.values():
            if isinstance(var.value, PointerValue) and not var.value.is_null:
                pointers.append((var.address, var.value.address, var.value))

        # Check stack
        for frame in snapshot.stack.frames:
            for var in frame.all_variables().values():
                if isinstance(var.value, PointerValue) and not var.value.is_null:
                    pointers.append((var.address, var.value.address, var.value))

        # Check heap
        for block in snapshot.heap.blocks.values():
            if not block.is_freed and isinstance(block.value, PointerValue) and not block.value.is_null:
                pointers.append((block.address, block.value.address, block.value))

        # Draw arrows for pointers that have both source and target positions
        for src_addr, tgt_addr, ptr_val in pointers:
            if src_addr in self.item_positions and tgt_addr in self.item_positions:
                self._draw_arrow(src_addr, tgt_addr)

    def _draw_arrow(self, from_addr: int, to_addr: int) -> None:
        """Draw an arrow from one address to another.

        Args:
            from_addr: Source address
            to_addr: Target address
        """
        # Get positions
        src_x, src_y, src_w, src_h = self.item_positions[from_addr]
        tgt_x, tgt_y, tgt_w, tgt_h = self.item_positions[to_addr]

        # Calculate arrow start and end points
        # Start from right edge of source
        start_x = src_x + src_w
        start_y = src_y + src_h // 2

        # End at left edge of target (or top if in same column)
        if tgt_x > src_x + src_w + 20:  # Target is to the right
            end_x = tgt_x
            end_y = tgt_y + tgt_h // 2
        else:  # Target is below or overlapping
            end_x = tgt_x + tgt_w // 2
            end_y = tgt_y

        # Draw the arrow line
        arrow_id = self.canvas.create_line(
            start_x, start_y,
            end_x, end_y,
            arrow=tk.LAST,
            fill=self.colors.POINTER_ARROW,
            width=2,
            smooth=True,
            arrowshape=(10, 12, 5)
        )

        # Lower the arrow so it's behind other items
        self.canvas.tag_lower(arrow_id)

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, PointerValue):
            if value.is_null:
                return "NULL"
            return f"→ {hex(value.address)}"
        elif isinstance(value, str):
            if len(value) > 20:
                return f'"{value[:17]}..."'
            return f'"{value}"'
        elif isinstance(value, dict):
            # For struct-like values
            items = ", ".join(f"{k}:{v}" for k, v in list(value.items())[:2])
            if len(value) > 2:
                items += ", ..."
            return f"{{{items}}}"
        else:
            s = str(value)
            return s if len(s) < 25 else s[:22] + "..."


# ============================================================
# Main GUI Window
# ============================================================

class MemoryVisualizer:
    """Main GUI window for memory visualization."""

    def __init__(self, snapshots: List[MemorySnapshot]):
        """Initialize the visualizer.

        Args:
            snapshots: List of memory snapshots to visualize
        """
        self.snapshots = snapshots
        self.current_index = 0

        # Create main window
        self.root = tk.Tk()
        self.root.title("Memory Model Visualizer")
        self.root.geometry("1200x800")

        # Color scheme
        self.colors = ColorScheme()

        # Create UI
        self._create_ui()

        # Render first snapshot
        if self.snapshots:
            self.show_snapshot(0)

    def _create_ui(self) -> None:
        """Create the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top toolbar
        self._create_toolbar(main_frame)

        # Content area (canvas + details)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas with scrollbars
        self._create_canvas(content_frame)

        # Right panel for details
        self._create_details_panel(content_frame)

        # Bottom status bar
        self._create_status_bar(main_frame)

    def _create_toolbar(self, parent: ttk.Frame) -> None:
        """Create the toolbar."""
        toolbar = ttk.Frame(parent, relief=tk.RAISED, borderwidth=1)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Navigation buttons
        ttk.Button(
            toolbar,
            text="◀◀ First",
            command=self.first_snapshot
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="◀ Previous",
            command=self.previous_snapshot
        ).pack(side=tk.LEFT, padx=2)

        # Current step label
        self.step_label = ttk.Label(toolbar, text="Step 0 / 0")
        self.step_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(
            toolbar,
            text="Next ▶",
            command=self.next_snapshot
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Last ▶▶",
            command=self.last_snapshot
        ).pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        # Slider
        ttk.Label(toolbar, text="Step:").pack(side=tk.LEFT, padx=5)
        self.step_slider = ttk.Scale(
            toolbar,
            from_=0,
            to=max(0, len(self.snapshots) - 1),
            orient=tk.HORIZONTAL,
            length=200,
            command=self._on_slider_change
        )
        self.step_slider.pack(side=tk.LEFT, padx=5)

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        # Export button
        ttk.Button(
            toolbar,
            text="Export Image",
            command=self.export_image
        ).pack(side=tk.LEFT, padx=2)

        # Refresh button
        ttk.Button(
            toolbar,
            text="⟳ Refresh",
            command=self.refresh
        ).pack(side=tk.LEFT, padx=2)

    def _create_canvas(self, parent: ttk.Frame) -> None:
        """Create the canvas area."""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create canvas with scrollbars
        self.canvas = tk.Canvas(
            canvas_frame,
            bg=self.colors.CANVAS_BG,
            scrollregion=(0, 0, 1000, 2000)
        )

        # Scrollbars
        h_scroll = ttk.Scrollbar(
            canvas_frame,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview
        )
        v_scroll = ttk.Scrollbar(
            canvas_frame,
            orient=tk.VERTICAL,
            command=self.canvas.yview
        )

        self.canvas.configure(
            xscrollcommand=h_scroll.set,
            yscrollcommand=v_scroll.set
        )

        # Pack widgets
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create renderer
        self.renderer = MemoryRenderer(self.canvas, self.colors)

        # Bind canvas events
        self.canvas.bind("<Button-1>", self._on_canvas_click)

    def _create_details_panel(self, parent: ttk.Frame) -> None:
        """Create the details panel."""
        details_frame = ttk.LabelFrame(parent, text="Details", width=250)
        details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)
        details_frame.pack_propagate(False)

        # Details text area
        self.details_text = scrolledtext.ScrolledText(
            details_frame,
            wrap=tk.WORD,
            width=30,
            height=20,
            font=("Courier", 9)
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_status_bar(self, parent: ttk.Frame) -> None:
        """Create the status bar."""
        status_frame = ttk.Frame(parent, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=2)

    def show_snapshot(self, index: int) -> None:
        """Show a specific snapshot.

        Args:
            index: Index of snapshot to show
        """
        if not self.snapshots or index < 0 or index >= len(self.snapshots):
            return

        self.current_index = index
        snapshot = self.snapshots[index]

        # Render snapshot
        self.renderer.render_snapshot(snapshot)

        # Update UI
        self.step_label.config(
            text=f"Step {index} / {len(self.snapshots) - 1}"
        )
        self.step_slider.set(index)

        # Update details panel
        self._update_details(snapshot)

        # Update status
        self.status_label.config(
            text=f"Showing step {snapshot.step_id}: {snapshot.description or '(no description)'}"
        )

    def _update_details(self, snapshot: MemorySnapshot) -> None:
        """Update the details panel with snapshot info."""
        self.details_text.delete("1.0", tk.END)

        lines = []
        lines.append(f"=== Step {snapshot.step_id} ===\n")
        if snapshot.description:
            lines.append(f"{snapshot.description}\n")
        lines.append("\n")

        # Stack info
        lines.append(f"Stack Depth: {snapshot.stack.depth()}\n")
        if snapshot.stack.frames:
            lines.append("Functions: ")
            lines.append(" → ".join(f.function_name for f in snapshot.stack.frames))
            lines.append("\n")
        lines.append("\n")

        # Heap info
        allocated = snapshot.heap.get_all_allocated()
        freed = snapshot.heap.get_all_freed()
        total_size = snapshot.heap.total_allocated_size()
        lines.append(f"Heap Blocks:\n")
        lines.append(f"  Allocated: {len(allocated)} ({total_size} bytes)\n")
        lines.append(f"  Freed: {len(freed)}\n")
        lines.append("\n")

        # Global info
        lines.append(f"Globals: {len(snapshot.globals_statics.variables)}\n")

        self.details_text.insert("1.0", "".join(lines))

    def _on_canvas_click(self, event) -> None:
        """Handle canvas click events."""
        # Find item under cursor
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)

        for item in items:
            if item in self.renderer.item_map:
                item_type, item_data = self.renderer.item_map[item]
                self._show_item_details(item_type, item_data)
                break

    def _show_item_details(self, item_type: str, item_data: Any) -> None:
        """Show details about a clicked item."""
        self.details_text.delete("1.0", tk.END)

        lines = []
        lines.append(f"=== {item_type.upper()} ===\n\n")

        if item_type == "global":
            var = item_data
            lines.append(f"Name: {var.name}\n")
            lines.append(f"Type: {var.type_name}\n")
            lines.append(f"Address: {hex(var.address)}\n")
            lines.append(f"Value: {var.value}\n")
            lines.append(f"Storage: {var.storage_class.value}\n")
            lines.append(f"Section: {var.section}\n")

        elif item_type in ("local", "param"):
            var = item_data
            lines.append(f"Name: {var.name}\n")
            lines.append(f"Type: {var.type_name}\n")
            lines.append(f"Address: {hex(var.address)}\n")
            lines.append(f"Value: {var.value}\n")

        elif item_type == "heap":
            block = item_data
            lines.append(f"Address: {hex(block.address)}\n")
            lines.append(f"Size: {block.size} bytes\n")
            lines.append(f"Type: {block.type_name}\n")
            lines.append(f"Status: {'FREED' if block.is_freed else 'ALLOCATED'}\n")
            if not block.is_freed:
                lines.append(f"Value: {block.value}\n")
            if block.allocation_site:
                lines.append(f"Allocated at: {block.allocation_site}\n")

        elif item_type == "frame":
            frame = item_data
            lines.append(f"Function: {frame.function_name}\n")
            lines.append(f"Parameters: {len(frame.parameters)}\n")
            lines.append(f"Locals: {len(frame.locals)}\n")
            if frame.return_address:
                lines.append(f"Return Address: {hex(frame.return_address)}\n")

        self.details_text.insert("1.0", "".join(lines))

    def _on_slider_change(self, value) -> None:
        """Handle slider value change."""
        index = int(float(value))
        if index != self.current_index:
            self.show_snapshot(index)

    def first_snapshot(self) -> None:
        """Go to first snapshot."""
        self.show_snapshot(0)

    def last_snapshot(self) -> None:
        """Go to last snapshot."""
        self.show_snapshot(len(self.snapshots) - 1)

    def previous_snapshot(self) -> None:
        """Go to previous snapshot."""
        if self.current_index > 0:
            self.show_snapshot(self.current_index - 1)

    def next_snapshot(self) -> None:
        """Go to next snapshot."""
        if self.current_index < len(self.snapshots) - 1:
            self.show_snapshot(self.current_index + 1)

    def refresh(self) -> None:
        """Refresh current view."""
        self.show_snapshot(self.current_index)

    def export_image(self) -> None:
        """Export current view to PostScript/image."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".ps",
            filetypes=[("PostScript", "*.ps"), ("All Files", "*.*")]
        )
        if filename:
            try:
                # Get canvas bounding box
                bbox = self.canvas.bbox("all")
                if bbox:
                    self.canvas.postscript(
                        file=filename,
                        colormode="color",
                        x=bbox[0],
                        y=bbox[1],
                        width=bbox[2] - bbox[0],
                        height=bbox[3] - bbox[1]
                    )
                    self.status_label.config(text=f"Exported to {filename}")
                    messagebox.showinfo("Export", f"Exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def run(self) -> None:
        """Run the GUI main loop."""
        self.root.mainloop()


# ============================================================
# Convenience function
# ============================================================

def visualize_snapshots(snapshots: List[MemorySnapshot]) -> None:
    """Convenience function to visualize snapshots.

    Args:
        snapshots: List of snapshots to visualize
    """
    visualizer = MemoryVisualizer(snapshots)
    visualizer.run()


if __name__ == "__main__":
    # Demo with example snapshots
    from memory_model import (
        create_initial_snapshot,
        SnapshotBuilder,
        GlobalStaticVariable,
        VariableStorageClass,
        PointerValue,
    )

    # Create some example snapshots
    g = GlobalStaticVariable(
        name="counter",
        address=0x4000,
        value=0,
        type_name="int",
        storage_class=VariableStorageClass.GLOBAL,
        section=".data",
    )

    snapshot0 = create_initial_snapshot(globals=[g], description="Program start")

    snapshot1 = (
        SnapshotBuilder(snapshot0)
        .push_frame("main")
        .set_step(1, "Entered main()")
        .build()
    )

    snapshot2 = (
        SnapshotBuilder(snapshot1)
        .set_local("x", 10, "int")
        .set_local("y", 20, "int")
        .set_step(2, "Declared x and y")
        .build()
    )

    builder3 = SnapshotBuilder(snapshot2)
    builder3, heap_addr = builder3.malloc(4, "int", 0, allocation_site="main:5")
    snapshot3 = (
        builder3
        .set_local("ptr", PointerValue(heap_addr, "int"), "int*")
        .set_step(3, "Allocated heap memory")
        .build()
    )

    snapshot4 = (
        SnapshotBuilder(snapshot3)
        .write_heap(heap_addr, 42)
        .set_step(4, "Wrote to heap")
        .build()
    )

    snapshots = [snapshot0, snapshot1, snapshot2, snapshot3, snapshot4]

    visualize_snapshots(snapshots)
