"""
memory_model.py

Library for modeling the memory state of a C program with console rendering.

This library provides:
- Data structures for modeling Stack, Heap, Global/Static segments
- Type registry for structs, unions, and typedefs
- SnapshotBuilder for creating memory state transitions
- Console rendering with configurable output
- Helper utilities for memory inspection and analysis

Example:
    >>> from memory_model import *
    >>>
    >>> # Create initial state
    >>> g = GlobalStaticVariable(
    ...     name="counter",
    ...     address=0x4040,
    ...     value=0,
    ...     type_name="int",
    ...     storage_class=VariableStorageClass.GLOBAL,
    ...     section=".data"
    ... )
    >>>
    >>> snapshot = create_initial_snapshot(globals=[g])
    >>> snapshot.print()
    >>>
    >>> # Create next state
    >>> snapshot2 = (
    ...     SnapshotBuilder(snapshot)
    ...     .push_frame("main")
    ...     .set_local("x", 10, "int")
    ...     .malloc(0x1000, 4, "int", 0)
    ...     .set_step(1, "After initialization")
    ...     .build()
    ... )
    >>> snapshot2.print()
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================
#  Configuration du rendu console
# ============================================================

@dataclass
class ConsoleRenderConfig:
    """Configuration for console rendering output.

    Attributes:
        pointer_arrow: Symbol to use for pointer visualization (→ or ->)
        show_addresses_hex: Display addresses in hexadecimal format
        max_struct_depth: Maximum nesting depth for struct rendering
        indent_size: Number of spaces per indentation level
        show_frame_pointers: Display frame pointer information
        compact_mode: Use more compact output format
    """
    pointer_arrow: str = "→"
    show_addresses_hex: bool = True
    max_struct_depth: int = 2
    indent_size: int = 2
    show_frame_pointers: bool = True
    compact_mode: bool = False


# Instance globale de configuration
render_config = ConsoleRenderConfig()


# ============================================================
#  Types de base : pointeurs, description de champs, struct, union
# ============================================================

@dataclass
class PointerValue:
    """Represents a pointer value with target address and type.

    Attributes:
        address: Memory address the pointer points to
        target_type: Type of the pointed-to value
        is_null: Whether this is a NULL pointer
    """
    address: int
    target_type: str
    is_null: bool = False

    def __str__(self) -> str:
        """Return string representation of the pointer."""
        if self.is_null:
            return "NULL"
        if render_config.show_addresses_hex:
            addr = hex(self.address)
        else:
            addr = str(self.address)
        return f"{render_config.pointer_arrow} {addr}"


@dataclass
class FieldDescriptor:
    """Describes a field within a struct or union.

    Attributes:
        name: Field name
        type_name: Type of the field
        offset: Byte offset from structure start
    """
    name: str
    type_name: str
    offset: int


@dataclass
class StructDescriptor:
    """Describes a C struct type.

    Attributes:
        name: Struct name
        fields: List of field descriptors
        size: Total size in bytes
    """
    name: str
    fields: List[FieldDescriptor]
    size: int


@dataclass
class UnionDescriptor:
    """Describes a C union type.

    Attributes:
        name: Union name
        fields: List of field descriptors (all at offset 0)
        size: Size in bytes (max of all fields)
    """
    name: str
    fields: List[FieldDescriptor]
    size: int


@dataclass
class TypeRegistry:
    """Registry of all user-defined types in the program.

    Attributes:
        structs: Dictionary mapping struct names to descriptors
        unions: Dictionary mapping union names to descriptors
        typedefs: Dictionary mapping typedef aliases to actual types
    """
    structs: Dict[str, StructDescriptor] = field(default_factory=dict)
    unions: Dict[str, UnionDescriptor] = field(default_factory=dict)
    typedefs: Dict[str, str] = field(default_factory=dict)

    def register_struct(self, struct: StructDescriptor) -> None:
        """Register a struct type."""
        self.structs[struct.name] = struct

    def register_union(self, union: UnionDescriptor) -> None:
        """Register a union type."""
        self.unions[union.name] = union

    def register_typedef(self, alias: str, real_type: str) -> None:
        """Register a typedef alias."""
        self.typedefs[alias] = real_type

    def resolve_type(self, type_name: str) -> str:
        """Resolve a type name through typedef chain."""
        while type_name in self.typedefs:
            type_name = self.typedefs[type_name]
        return type_name

    def to_console(self) -> str:
        """Render type registry to console format."""
        lines: List[str] = []
        lines.append("=== Types (Struct / Union / Typedef) ===")
        if not self.structs and not self.unions and not self.typedefs:
            lines.append("(no types defined)")
            return "\n".join(lines)

        if self.structs:
            lines.append("-- Structs --")
            for name, desc in self.structs.items():
                lines.append(f"struct {name} (size={desc.size} bytes)")
                for f in desc.fields:
                    lines.append(f"  + {f.name:15} : {f.type_name:20} @ offset {f.offset}")

        if self.unions:
            lines.append("-- Unions --")
            for name, desc in self.unions.items():
                lines.append(f"union {name} (size={desc.size} bytes)")
                for f in desc.fields:
                    lines.append(f"  + {f.name:15} : {f.type_name}")

        if self.typedefs:
            lines.append("-- Typedefs --")
            for alias, real in self.typedefs.items():
                lines.append(f"typedef {alias:20} = {real}")

        return "\n".join(lines)

    def print(self) -> None:
        """Print type registry to console."""
        print(self.to_console())


# ============================================================
#  Globals & statics
# ============================================================

class VariableStorageClass(Enum):
    """Storage class for variables."""
    GLOBAL = "global"
    STATIC = "static"


@dataclass
class GlobalStaticVariable:
    """Represents a global or static variable.

    Attributes:
        name: Variable name
        address: Memory address
        value: Current value
        type_name: Type of the variable
        storage_class: GLOBAL or STATIC
        section: Memory section (.data, .bss, .rodata, etc.)
    """
    name: str
    address: int
    value: Any
    type_name: str
    storage_class: VariableStorageClass
    section: str

    def __deepcopy__(self, memo: Dict[int, Any]) -> GlobalStaticVariable:
        """Create a deep copy of the variable."""
        return GlobalStaticVariable(
            name=self.name,
            address=self.address,
            value=copy.deepcopy(self.value, memo),
            type_name=self.type_name,
            storage_class=self.storage_class,
            section=self.section,
        )


@dataclass
class GlobalStaticSegment:
    """Represents the global and static variable segment.

    Attributes:
        variables: Dictionary mapping variable names to variables
    """
    variables: Dict[str, GlobalStaticVariable] = field(default_factory=dict)

    def get_variable(self, name: str) -> Optional[GlobalStaticVariable]:
        """Get a global/static variable by name."""
        return self.variables.get(name)

    def get_by_address(self, address: int) -> Optional[GlobalStaticVariable]:
        """Get a global/static variable by address."""
        for var in self.variables.values():
            if var.address == address:
                return var
        return None

    def to_console(self) -> str:
        """Render globals/statics to console format."""
        lines: List[str] = []
        lines.append("=== Global & Static Variables ===")
        if not self.variables:
            lines.append("(no global/static variables)")
            return "\n".join(lines)

        header = f"{'Name':20} {'Address':12} {'Type':18} {'Value':15} {'Section':10}"
        lines.append(header)
        lines.append("-" * len(header))

        for var in self.variables.values():
            addr = hex(var.address) if render_config.show_addresses_hex else str(var.address)
            val_str = self._format_value(var.value)
            line = f"{var.name:20} {addr:12} {var.type_name:18} {val_str:15} {var.section:10}"
            lines.append(line)

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, PointerValue):
            return str(value)
        elif isinstance(value, str):
            return f'"{value}"' if len(value) < 12 else f'"{value[:9]}..."'
        else:
            s = str(value)
            return s if len(s) < 15 else s[:12] + "..."

    def print(self) -> None:
        """Print globals/statics to console."""
        print(self.to_console())

    def __deepcopy__(self, memo: Dict[int, Any]) -> GlobalStaticSegment:
        """Create a deep copy of the segment."""
        return GlobalStaticSegment(
            variables={k: copy.deepcopy(v, memo) for k, v in self.variables.items()}
        )


# ============================================================
#  Heap
# ============================================================

@dataclass
class HeapBlock:
    """Represents an allocated block on the heap.

    Attributes:
        address: Starting address of the block
        size: Size in bytes
        value: Current value stored in the block
        type_name: Type of data stored
        is_freed: Whether the block has been freed
        allocation_site: Optional description of where allocated
    """
    address: int
    size: int
    value: Any
    type_name: str
    is_freed: bool = False
    allocation_site: Optional[str] = None

    def __deepcopy__(self, memo: Dict[int, Any]) -> HeapBlock:
        """Create a deep copy of the heap block."""
        return HeapBlock(
            address=self.address,
            size=self.size,
            value=copy.deepcopy(self.value, memo),
            type_name=self.type_name,
            is_freed=self.is_freed,
            allocation_site=self.allocation_site,
        )


@dataclass
class HeapSegment:
    """Represents the heap segment.

    Attributes:
        blocks: Dictionary mapping addresses to heap blocks
    """
    blocks: Dict[int, HeapBlock] = field(default_factory=dict)

    def get_block(self, address: int) -> Optional[HeapBlock]:
        """Get a heap block by address."""
        return self.blocks.get(address)

    def get_all_allocated(self) -> List[HeapBlock]:
        """Get all currently allocated (not freed) blocks."""
        return [b for b in self.blocks.values() if not b.is_freed]

    def get_all_freed(self) -> List[HeapBlock]:
        """Get all freed blocks."""
        return [b for b in self.blocks.values() if b.is_freed]

    def total_allocated_size(self) -> int:
        """Calculate total size of allocated blocks."""
        return sum(b.size for b in self.blocks.values() if not b.is_freed)

    def find_leaks(self, reachable_addresses: Set[int]) -> List[HeapBlock]:
        """Find potentially leaked blocks (allocated but not reachable)."""
        return [
            b for b in self.blocks.values()
            if not b.is_freed and b.address not in reachable_addresses
        ]

    def to_console(self) -> str:
        """Render heap to console format."""
        lines: List[str] = []
        lines.append("=== Heap ===")
        if not self.blocks:
            lines.append("(no allocations)")
            return "\n".join(lines)

        allocated = self.get_all_allocated()
        freed = self.get_all_freed()

        lines.append(f"Total allocated: {len(allocated)} blocks ({self.total_allocated_size()} bytes)")
        lines.append(f"Freed: {len(freed)} blocks")
        lines.append("")

        header = f"{'Address':12} {'Size':8} {'Type':18} {'Status':8} {'Value'}"
        lines.append(header)
        lines.append("-" * len(header))

        # Sort by address
        for addr in sorted(self.blocks.keys()):
            block = self.blocks[addr]
            a = hex(addr) if render_config.show_addresses_hex else str(addr)
            status = "freed" if block.is_freed else "active"
            val = "<freed>" if block.is_freed else self._format_value(block.value)
            line = f"{a:12} {block.size:<8} {block.type_name:18} {status:8} {val}"
            lines.append(line)
            if block.allocation_site and not render_config.compact_mode:
                lines.append(f"  └─ allocated at: {block.allocation_site}")

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, PointerValue):
            return str(value)
        elif isinstance(value, str):
            return f'"{value}"' if len(value) < 20 else f'"{value[:17]}..."'
        else:
            s = str(value)
            return s if len(s) < 30 else s[:27] + "..."

    def print(self) -> None:
        """Print heap to console."""
        print(self.to_console())

    def __deepcopy__(self, memo: Dict[int, Any]) -> HeapSegment:
        """Create a deep copy of the segment."""
        return HeapSegment(
            blocks={k: copy.deepcopy(v, memo) for k, v in self.blocks.items()}
        )


# ============================================================
#  Stack
# ============================================================

@dataclass
class StackVariable:
    """Represents a variable on the stack.

    Attributes:
        name: Variable name
        address: Memory address
        value: Current value
        type_name: Type of the variable
    """
    name: str
    address: int
    value: Any
    type_name: str

    def __deepcopy__(self, memo: Dict[int, Any]) -> StackVariable:
        """Create a deep copy of the variable."""
        return StackVariable(
            name=self.name,
            address=self.address,
            value=copy.deepcopy(self.value, memo),
            type_name=self.type_name,
        )


@dataclass
class StackFrame:
    """Represents a stack frame for a function call.

    Attributes:
        function_name: Name of the function
        locals: Dictionary of local variables
        parameters: Dictionary of function parameters
        return_address: Return address for the function
        frame_pointer: Frame pointer (base pointer)
    """
    function_name: str
    locals: Dict[str, StackVariable] = field(default_factory=dict)
    parameters: Dict[str, StackVariable] = field(default_factory=dict)
    return_address: Optional[int] = None
    frame_pointer: Optional[int] = None

    def get_variable(self, name: str) -> Optional[StackVariable]:
        """Get a variable (parameter or local) by name."""
        if name in self.parameters:
            return self.parameters[name]
        return self.locals.get(name)

    def all_variables(self) -> Dict[str, StackVariable]:
        """Get all variables in this frame (parameters + locals)."""
        result = dict(self.parameters)
        result.update(self.locals)
        return result

    def to_console(self) -> str:
        """Render stack frame to console format."""
        lines: List[str] = []
        lines.append(f"┌─ Frame: {self.function_name} ─┐")

        if render_config.show_frame_pointers and self.frame_pointer is not None:
            fp = hex(self.frame_pointer) if render_config.show_addresses_hex else str(self.frame_pointer)
            lines.append(f"│ Frame Pointer: {fp}")

        if self.parameters:
            lines.append("│ Parameters:")
            for var in self.parameters.values():
                addr = hex(var.address) if render_config.show_addresses_hex else str(var.address)
                val = self._format_value(var.value)
                lines.append(f"│   {var.name:15} @{addr:<12} {var.type_name:12} = {val}")

        if self.locals:
            lines.append("│ Locals:")
            for var in self.locals.values():
                addr = hex(var.address) if render_config.show_addresses_hex else str(var.address)
                val = self._format_value(var.value)
                lines.append(f"│   {var.name:15} @{addr:<12} {var.type_name:12} = {val}")

        if not self.parameters and not self.locals:
            lines.append("│   (no variables)")

        lines.append("└" + "─" * (len(lines[0]) - 1))
        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, PointerValue):
            return str(value)
        elif isinstance(value, str):
            return f'"{value}"' if len(value) < 15 else f'"{value[:12]}..."'
        else:
            s = str(value)
            return s if len(s) < 20 else s[:17] + "..."

    def __deepcopy__(self, memo: Dict[int, Any]) -> StackFrame:
        """Create a deep copy of the frame."""
        return StackFrame(
            function_name=self.function_name,
            locals={k: copy.deepcopy(v, memo) for k, v in self.locals.items()},
            parameters={k: copy.deepcopy(v, memo) for k, v in self.parameters.items()},
            return_address=self.return_address,
            frame_pointer=self.frame_pointer,
        )


@dataclass
class StackSegment:
    """Represents the stack segment.

    Attributes:
        frames: List of stack frames (bottom to top)
    """
    frames: List[StackFrame] = field(default_factory=list)

    def current_frame(self) -> Optional[StackFrame]:
        """Get the current (topmost) stack frame."""
        return self.frames[-1] if self.frames else None

    def find_variable(self, name: str) -> Optional[Tuple[int, StackVariable]]:
        """Find a variable by name in the stack (top to bottom search).

        Returns:
            Tuple of (frame_index, variable) or None if not found
        """
        for i in range(len(self.frames) - 1, -1, -1):
            var = self.frames[i].get_variable(name)
            if var is not None:
                return (i, var)
        return None

    def depth(self) -> int:
        """Get the current stack depth (number of frames)."""
        return len(self.frames)

    def to_console(self) -> str:
        """Render stack to console format."""
        lines: List[str] = []
        lines.append("=== Stack ===")
        if not self.frames:
            lines.append("(empty stack)")
            return "\n".join(lines)

        lines.append(f"Depth: {len(self.frames)} frame(s)")
        lines.append("")

        # Render from bottom to top
        for i, frame in enumerate(self.frames):
            if i > 0:
                lines.append("")
            lines.append(frame.to_console())

        return "\n".join(lines)

    def print(self) -> None:
        """Print stack to console."""
        print(self.to_console())

    def __deepcopy__(self, memo: Dict[int, Any]) -> StackSegment:
        """Create a deep copy of the segment."""
        return StackSegment(
            frames=[copy.deepcopy(f, memo) for f in self.frames]
        )


# ============================================================
#  CPU
# ============================================================

@dataclass
class CpuState:
    """Represents CPU register state.

    Attributes:
        pc: Program counter (instruction pointer)
        sp: Stack pointer
        bp: Base pointer (frame pointer)
        extra: Additional registers or state
    """
    pc: Optional[int] = None
    sp: Optional[int] = None
    bp: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_console(self) -> str:
        """Render CPU state to console format."""
        lines: List[str] = []
        lines.append("=== CPU State ===")

        def fmt_addr(addr: Optional[int]) -> str:
            if addr is None:
                return "(not set)"
            return hex(addr) if render_config.show_addresses_hex else str(addr)

        lines.append(f"PC (Program Counter): {fmt_addr(self.pc)}")
        lines.append(f"SP (Stack Pointer):   {fmt_addr(self.sp)}")
        lines.append(f"BP (Base Pointer):    {fmt_addr(self.bp)}")

        if self.extra:
            lines.append("Extra registers:")
            for reg, val in self.extra.items():
                lines.append(f"  {reg:10} : {val}")

        return "\n".join(lines)

    def print(self) -> None:
        """Print CPU state to console."""
        print(self.to_console())

    def __deepcopy__(self, memo: Dict[int, Any]) -> CpuState:
        """Create a deep copy of CPU state."""
        return CpuState(
            pc=self.pc,
            sp=self.sp,
            bp=self.bp,
            extra=copy.deepcopy(self.extra, memo),
        )


# ============================================================
#  MemorySnapshot
# ============================================================

@dataclass
class MemorySnapshot:
    """Represents a complete snapshot of program memory at a point in time.

    Attributes:
        step_id: Unique identifier for this snapshot
        description: Human-readable description of this state
        globals_statics: Global and static variables segment
        heap: Heap segment
        stack: Stack segment
        types: Type registry
        cpu: CPU state (optional)
    """
    step_id: int
    description: Optional[str]
    globals_statics: GlobalStaticSegment
    heap: HeapSegment
    stack: StackSegment
    types: TypeRegistry
    cpu: Optional[CpuState] = None

    def get_value_at_address(self, address: int) -> Optional[Any]:
        """Look up a value by memory address across all segments."""
        # Check globals
        var = self.globals_statics.get_by_address(address)
        if var:
            return var.value

        # Check heap
        block = self.heap.get_block(address)
        if block and not block.is_freed:
            return block.value

        # Check stack (all frames)
        for frame in self.stack.frames:
            for var in frame.all_variables().values():
                if var.address == address:
                    return var.value

        return None

    def find_all_pointers_to(self, target_address: int) -> List[Tuple[str, int]]:
        """Find all pointers pointing to a given address.

        Returns:
            List of (location_description, pointer_address) tuples
        """
        pointers: List[Tuple[str, int]] = []

        # Check globals
        for var in self.globals_statics.variables.values():
            if isinstance(var.value, PointerValue) and var.value.address == target_address:
                pointers.append((f"global {var.name}", var.address))

        # Check heap
        for block in self.heap.blocks.values():
            if not block.is_freed and isinstance(block.value, PointerValue):
                if block.value.address == target_address:
                    pointers.append((f"heap block @ {hex(block.address)}", block.address))

        # Check stack
        for i, frame in enumerate(self.stack.frames):
            for var in frame.all_variables().values():
                if isinstance(var.value, PointerValue) and var.value.address == target_address:
                    pointers.append((f"stack {frame.function_name}::{var.name}", var.address))

        return pointers

    def to_console(self, show_types: bool = False) -> str:
        """Render complete memory snapshot to console format.

        Args:
            show_types: Whether to include type registry in output
        """
        lines: List[str] = []
        lines.append("=" * 70)
        if self.description:
            lines.append(f" Step {self.step_id}: {self.description}")
        else:
            lines.append(f" Step {self.step_id}")
        lines.append("=" * 70)
        lines.append("")

        if show_types and (self.types.structs or self.types.unions or self.types.typedefs):
            lines.append(self.types.to_console())
            lines.append("")

        lines.append(self.globals_statics.to_console())
        lines.append("")
        lines.append(self.stack.to_console())
        lines.append("")
        lines.append(self.heap.to_console())

        if self.cpu is not None:
            lines.append("")
            lines.append(self.cpu.to_console())

        return "\n".join(lines)

    def print(self, show_types: bool = False) -> None:
        """Print memory snapshot to console.

        Args:
            show_types: Whether to include type registry in output
        """
        print(self.to_console(show_types=show_types))


# ============================================================
#  Création d'un snapshot initial
# ============================================================

def create_initial_snapshot(
    globals: Optional[List[GlobalStaticVariable]] = None,
    types: Optional[TypeRegistry] = None,
    cpu: Optional[CpuState] = None,
    step_id: int = 0,
    description: Optional[str] = "Initial state",
) -> MemorySnapshot:
    """Create an initial memory snapshot.

    Args:
        globals: List of global/static variables
        types: Type registry (optional)
        cpu: CPU state (optional)
        step_id: Step identifier
        description: Description of this state

    Returns:
        A new MemorySnapshot instance
    """
    globals_list = globals if globals is not None else []
    gs_segment = GlobalStaticSegment(variables={v.name: v for v in globals_list})
    heap_segment = HeapSegment()
    stack_segment = StackSegment()
    type_registry = types if types is not None else TypeRegistry()

    return MemorySnapshot(
        step_id=step_id,
        description=description,
        globals_statics=gs_segment,
        heap=heap_segment,
        stack=stack_segment,
        types=type_registry,
        cpu=cpu,
    )


# ============================================================
#  SnapshotBuilder
# ============================================================

class SnapshotBuilder:
    """Builder for creating new memory snapshots from existing ones.

    This builder creates deep copies of the base snapshot to ensure
    immutability. It provides a fluent API for making memory modifications.

    Example:
        >>> builder = SnapshotBuilder(snapshot0)
        >>> snapshot1 = (
        ...     builder
        ...     .push_frame("main")
        ...     .set_local("x", 10, "int")
        ...     .set_step(1, "After int x = 10")
        ...     .build()
        ... )
    """

    def __init__(self, base: MemorySnapshot) -> None:
        """Initialize builder with a base snapshot.

        Args:
            base: The snapshot to build upon (will be deep copied)
        """
        self._base = base
        # Deep copy all mutable state
        self._globals = copy.deepcopy(base.globals_statics)
        self._heap = copy.deepcopy(base.heap)
        self._stack = copy.deepcopy(base.stack)
        self._types = base.types  # Types are typically immutable
        self._cpu = copy.deepcopy(base.cpu) if base.cpu else None
        self._step_id: Optional[int] = None
        self._description: Optional[str] = None
        self._next_stack_addr = 0x7fff_0000  # Default stack address counter
        self._next_heap_addr = 0x1000  # Default heap address counter

    # ------------- Stack operations ------------- #

    def push_frame(
        self,
        function_name: str,
        return_address: Optional[int] = None,
        frame_pointer: Optional[int] = None,
    ) -> "SnapshotBuilder":
        """Push a new stack frame.

        Args:
            function_name: Name of the function
            return_address: Return address (optional)
            frame_pointer: Frame pointer value (optional)

        Returns:
            Self for chaining
        """
        frame = StackFrame(
            function_name=function_name,
            return_address=return_address,
            frame_pointer=frame_pointer,
        )
        self._stack.frames.append(frame)
        return self

    def pop_frame(self) -> "SnapshotBuilder":
        """Pop the current stack frame.

        Returns:
            Self for chaining

        Raises:
            RuntimeError: If stack is empty
        """
        if not self._stack.frames:
            raise RuntimeError("Cannot pop frame: stack is empty")
        self._stack.frames.pop()
        return self

    def set_local(
        self,
        name: str,
        value: Any,
        type_name: str,
        address: Optional[int] = None,
    ) -> "SnapshotBuilder":
        """Set a local variable in the current stack frame.

        Args:
            name: Variable name
            value: Variable value
            type_name: Type of the variable
            address: Memory address (auto-generated if None)

        Returns:
            Self for chaining

        Raises:
            RuntimeError: If no frame exists on the stack
        """
        if not self._stack.frames:
            raise RuntimeError("No frame on stack for set_local()")
        frame = self._stack.frames[-1]

        if address is None:
            address = self._next_stack_addr
            self._next_stack_addr += 8  # Assume 8-byte alignment

        frame.locals[name] = StackVariable(
            name=name,
            address=address,
            value=value,
            type_name=type_name,
        )
        return self

    def set_parameter(
        self,
        name: str,
        value: Any,
        type_name: str,
        address: Optional[int] = None,
    ) -> "SnapshotBuilder":
        """Set a function parameter in the current stack frame.

        Args:
            name: Parameter name
            value: Parameter value
            type_name: Type of the parameter
            address: Memory address (auto-generated if None)

        Returns:
            Self for chaining

        Raises:
            RuntimeError: If no frame exists on the stack
        """
        if not self._stack.frames:
            raise RuntimeError("No frame on stack for set_parameter()")
        frame = self._stack.frames[-1]

        if address is None:
            address = self._next_stack_addr
            self._next_stack_addr += 8

        frame.parameters[name] = StackVariable(
            name=name,
            address=address,
            value=value,
            type_name=type_name,
        )
        return self

    def update_local(self, name: str, new_value: Any) -> "SnapshotBuilder":
        """Update the value of an existing local variable.

        Args:
            name: Variable name
            new_value: New value

        Returns:
            Self for chaining

        Raises:
            RuntimeError: If variable not found
        """
        if not self._stack.frames:
            raise RuntimeError("No frame on stack")
        frame = self._stack.frames[-1]
        if name not in frame.locals:
            raise RuntimeError(f"Local variable '{name}' not found in current frame")
        frame.locals[name].value = new_value
        return self

    # ------------- Heap operations ------------- #

    def malloc(
        self,
        size: int,
        type_name: str,
        initial_value: Any = None,
        address: Optional[int] = None,
        allocation_site: Optional[str] = None,
    ) -> Tuple["SnapshotBuilder", int]:
        """Allocate memory on the heap.

        Args:
            size: Size in bytes
            type_name: Type of allocation
            initial_value: Initial value (defaults to 0)
            address: Specific address to use (auto-generated if None)
            allocation_site: Description of where allocated

        Returns:
            Tuple of (self for chaining, allocated address)

        Raises:
            ValueError: If address already in use
        """
        if address is None:
            # Find next available address
            while self._next_heap_addr in self._heap.blocks:
                self._next_heap_addr += 0x100
            address = self._next_heap_addr
            self._next_heap_addr += 0x100

        if address in self._heap.blocks and not self._heap.blocks[address].is_freed:
            raise ValueError(f"Address {hex(address)} already allocated")

        value = initial_value if initial_value is not None else 0
        self._heap.blocks[address] = HeapBlock(
            address=address,
            size=size,
            value=value,
            type_name=type_name,
            is_freed=False,
            allocation_site=allocation_site,
        )
        return self, address

    def free(self, address: int) -> "SnapshotBuilder":
        """Free a heap block.

        Args:
            address: Address of block to free

        Returns:
            Self for chaining

        Raises:
            KeyError: If block not found
            ValueError: If block already freed (double free)
        """
        block = self._heap.blocks.get(address)
        if block is None:
            raise KeyError(f"No heap block at address {hex(address)}")
        if block.is_freed:
            raise ValueError(f"Double free detected at address {hex(address)}")
        block.is_freed = True
        return self

    def write_heap(self, address: int, new_value: Any) -> "SnapshotBuilder":
        """Write a new value to a heap block.

        Args:
            address: Address of the block
            new_value: New value to write

        Returns:
            Self for chaining

        Raises:
            KeyError: If block not found
            ValueError: If writing to freed memory
        """
        block = self._heap.blocks.get(address)
        if block is None:
            raise KeyError(f"No heap block at address {hex(address)}")
        if block.is_freed:
            raise ValueError(f"Cannot write to freed memory at {hex(address)}")
        block.value = new_value
        return self

    def read_heap(self, address: int) -> Any:
        """Read the value from a heap block.

        Args:
            address: Address of the block

        Returns:
            The value stored in the block

        Raises:
            KeyError: If block not found
            ValueError: If reading freed memory
        """
        block = self._heap.blocks.get(address)
        if block is None:
            raise KeyError(f"No heap block at address {hex(address)}")
        if block.is_freed:
            raise ValueError(f"Cannot read freed memory at {hex(address)}")
        return block.value

    # ------------- Global/Static operations ------------- #

    def set_global(self, name: str, new_value: Any) -> "SnapshotBuilder":
        """Update a global/static variable.

        Args:
            name: Variable name
            new_value: New value

        Returns:
            Self for chaining

        Raises:
            KeyError: If variable not found
        """
        var = self._globals.variables.get(name)
        if var is None:
            raise KeyError(f"No global/static variable named '{name}'")
        var.value = new_value
        return self

    def add_global(self, variable: GlobalStaticVariable) -> "SnapshotBuilder":
        """Add a new global/static variable.

        Args:
            variable: The variable to add

        Returns:
            Self for chaining
        """
        self._globals.variables[variable.name] = variable
        return self

    # ------------- CPU operations ------------- #

    def set_pc(self, pc: int) -> "SnapshotBuilder":
        """Set the program counter.

        Args:
            pc: New program counter value

        Returns:
            Self for chaining
        """
        if self._cpu is None:
            self._cpu = CpuState(pc=pc)
        else:
            self._cpu.pc = pc
        return self

    def set_sp(self, sp: int) -> "SnapshotBuilder":
        """Set the stack pointer.

        Args:
            sp: New stack pointer value

        Returns:
            Self for chaining
        """
        if self._cpu is None:
            self._cpu = CpuState(sp=sp)
        else:
            self._cpu.sp = sp
        return self

    def set_bp(self, bp: int) -> "SnapshotBuilder":
        """Set the base pointer.

        Args:
            bp: New base pointer value

        Returns:
            Self for chaining
        """
        if self._cpu is None:
            self._cpu = CpuState(bp=bp)
        else:
            self._cpu.bp = bp
        return self

    # ------------- Metadata operations ------------- #

    def set_step(
        self,
        step_id: int,
        description: Optional[str] = None,
    ) -> "SnapshotBuilder":
        """Set the step ID and description for the next snapshot.

        Args:
            step_id: Step identifier
            description: Step description

        Returns:
            Self for chaining
        """
        self._step_id = step_id
        self._description = description
        return self

    # ------------- Build ------------- #

    def build(
        self,
        step_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> MemorySnapshot:
        """Build the final snapshot.

        Args:
            step_id: Override step ID (uses set_step value if None)
            description: Override description (uses set_step value if None)

        Returns:
            A new MemorySnapshot instance
        """
        sid = step_id if step_id is not None else (
            self._step_id if self._step_id is not None else self._base.step_id + 1
        )
        desc = description if description is not None else self._description

        return MemorySnapshot(
            step_id=sid,
            description=desc,
            globals_statics=self._globals,
            heap=self._heap,
            stack=self._stack,
            types=self._types,
            cpu=self._cpu,
        )


# ============================================================
#  Utility functions
# ============================================================

def diff_snapshots(old: MemorySnapshot, new: MemorySnapshot) -> str:
    """Create a textual diff between two snapshots.

    Args:
        old: Earlier snapshot
        new: Later snapshot

    Returns:
        A string describing the changes
    """
    changes: List[str] = []
    changes.append(f"=== Changes from Step {old.step_id} to Step {new.step_id} ===")
    changes.append("")

    # Global changes
    global_changes = []
    for name, var in new.globals_statics.variables.items():
        old_var = old.globals_statics.variables.get(name)
        if old_var is None:
            global_changes.append(f"  + Added global '{name}' = {var.value}")
        elif old_var.value != var.value:
            global_changes.append(f"  ~ Changed '{name}': {old_var.value} → {var.value}")

    for name in old.globals_statics.variables:
        if name not in new.globals_statics.variables:
            global_changes.append(f"  - Removed global '{name}'")

    if global_changes:
        changes.append("Globals/Statics:")
        changes.extend(global_changes)
        changes.append("")

    # Stack changes
    stack_changes = []
    old_depth = len(old.stack.frames)
    new_depth = len(new.stack.frames)

    if new_depth > old_depth:
        for i in range(old_depth, new_depth):
            stack_changes.append(f"  + Pushed frame: {new.stack.frames[i].function_name}")
    elif new_depth < old_depth:
        for i in range(new_depth, old_depth):
            stack_changes.append(f"  - Popped frame: {old.stack.frames[i].function_name}")

    # Check for variable changes in common frames
    for i in range(min(old_depth, new_depth)):
        old_frame = old.stack.frames[i]
        new_frame = new.stack.frames[i]

        for name, var in new_frame.all_variables().items():
            old_var = old_frame.get_variable(name)
            if old_var is None:
                stack_changes.append(
                    f"  + Added {new_frame.function_name}::{name} = {var.value}"
                )
            elif old_var.value != var.value:
                stack_changes.append(
                    f"  ~ Changed {new_frame.function_name}::{name}: "
                    f"{old_var.value} → {var.value}"
                )

    if stack_changes:
        changes.append("Stack:")
        changes.extend(stack_changes)
        changes.append("")

    # Heap changes
    heap_changes = []
    for addr, block in new.heap.blocks.items():
        old_block = old.heap.blocks.get(addr)
        if old_block is None:
            heap_changes.append(
                f"  + Allocated {block.size} bytes at {hex(addr)} ({block.type_name})"
            )
        elif old_block.is_freed != block.is_freed:
            if block.is_freed:
                heap_changes.append(f"  - Freed block at {hex(addr)}")
        elif old_block.value != block.value and not block.is_freed:
            heap_changes.append(
                f"  ~ Changed block at {hex(addr)}: {old_block.value} → {block.value}"
            )

    if heap_changes:
        changes.append("Heap:")
        changes.extend(heap_changes)
        changes.append("")

    if len(changes) == 2:  # Only header and empty line
        changes.append("(no changes)")

    return "\n".join(changes)


# ============================================================
#  Example usage
# ============================================================

if __name__ == "__main__":
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
    print("=" * 70)
    print("INITIAL STATE")
    print("=" * 70)
    snapshot0.print()

    print("\n\n")

    # Create snapshot after entering main and allocating memory
    builder = SnapshotBuilder(snapshot0)
    builder, heap_addr = builder.malloc(4, "int", 0, allocation_site="main:5")

    snapshot1 = (
        builder
        .push_frame("main")
        .set_local("x", 10, "int")
        .set_local("ptr", PointerValue(heap_addr, "int"), "int*")
        .set_step(1, "After int x = 10 and int* ptr = malloc(sizeof(int))")
        .build()
    )

    print("=" * 70)
    print("AFTER INITIALIZATION")
    print("=" * 70)
    snapshot1.print()

    print("\n\n")
    print("=" * 70)
    print("DIFF")
    print("=" * 70)
    print(diff_snapshots(snapshot0, snapshot1))
