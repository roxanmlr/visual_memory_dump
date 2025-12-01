"""
test_memory_model.py

Comprehensive unit tests for the memory_model library.
"""

import pytest
from memory_model import (
    # Core classes
    MemorySnapshot,
    SnapshotBuilder,
    GlobalStaticVariable,
    GlobalStaticSegment,
    HeapBlock,
    HeapSegment,
    StackVariable,
    StackFrame,
    StackSegment,
    CpuState,
    # Type system
    TypeRegistry,
    StructDescriptor,
    UnionDescriptor,
    FieldDescriptor,
    PointerValue,
    # Enums
    VariableStorageClass,
    # Functions
    create_initial_snapshot,
    diff_snapshots,
    render_config,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_global():
    """Create a sample global variable."""
    return GlobalStaticVariable(
        name="g_count",
        address=0x4000,
        value=42,
        type_name="int",
        storage_class=VariableStorageClass.GLOBAL,
        section=".data",
    )


@pytest.fixture
def sample_static():
    """Create a sample static variable."""
    return GlobalStaticVariable(
        name="s_flag",
        address=0x4008,
        value=True,
        type_name="bool",
        storage_class=VariableStorageClass.STATIC,
        section=".bss",
    )


@pytest.fixture
def basic_snapshot(sample_global):
    """Create a basic memory snapshot."""
    return create_initial_snapshot(
        globals=[sample_global],
        step_id=0,
        description="Test snapshot",
    )


@pytest.fixture
def sample_struct():
    """Create a sample struct descriptor."""
    return StructDescriptor(
        name="Point",
        fields=[
            FieldDescriptor("x", "int", 0),
            FieldDescriptor("y", "int", 4),
        ],
        size=8,
    )


# ============================================================
# TypeRegistry Tests
# ============================================================

class TestTypeRegistry:
    """Tests for TypeRegistry."""

    def test_empty_registry(self):
        """Test empty type registry."""
        registry = TypeRegistry()
        assert len(registry.structs) == 0
        assert len(registry.unions) == 0
        assert len(registry.typedefs) == 0

    def test_register_struct(self, sample_struct):
        """Test registering a struct."""
        registry = TypeRegistry()
        registry.register_struct(sample_struct)
        assert "Point" in registry.structs
        assert registry.structs["Point"] == sample_struct

    def test_register_union(self):
        """Test registering a union."""
        registry = TypeRegistry()
        union = UnionDescriptor(
            name="Data",
            fields=[
                FieldDescriptor("i", "int", 0),
                FieldDescriptor("f", "float", 0),
            ],
            size=4,
        )
        registry.register_union(union)
        assert "Data" in registry.unions
        assert registry.unions["Data"] == union

    def test_register_typedef(self):
        """Test registering a typedef."""
        registry = TypeRegistry()
        registry.register_typedef("MyInt", "int")
        assert registry.typedefs["MyInt"] == "int"

    def test_resolve_type_simple(self):
        """Test resolving a simple typedef."""
        registry = TypeRegistry()
        registry.register_typedef("MyInt", "int")
        assert registry.resolve_type("MyInt") == "int"
        assert registry.resolve_type("int") == "int"

    def test_resolve_type_chain(self):
        """Test resolving a typedef chain."""
        registry = TypeRegistry()
        registry.register_typedef("A", "B")
        registry.register_typedef("B", "C")
        registry.register_typedef("C", "int")
        assert registry.resolve_type("A") == "int"

    def test_to_console(self, sample_struct):
        """Test console rendering."""
        registry = TypeRegistry()
        registry.register_struct(sample_struct)
        output = registry.to_console()
        assert "struct Point" in output
        assert "size=8" in output


# ============================================================
# PointerValue Tests
# ============================================================

class TestPointerValue:
    """Tests for PointerValue."""

    def test_pointer_value_creation(self):
        """Test creating a pointer value."""
        ptr = PointerValue(0x1000, "int")
        assert ptr.address == 0x1000
        assert ptr.target_type == "int"
        assert not ptr.is_null

    def test_null_pointer(self):
        """Test NULL pointer."""
        ptr = PointerValue(0, "void", is_null=True)
        assert ptr.is_null
        assert str(ptr) == "NULL"

    def test_pointer_string_hex(self):
        """Test pointer string representation in hex."""
        render_config.show_addresses_hex = True
        ptr = PointerValue(0x1000, "int")
        s = str(ptr)
        assert "0x1000" in s

    def test_pointer_string_decimal(self):
        """Test pointer string representation in decimal."""
        render_config.show_addresses_hex = False
        ptr = PointerValue(4096, "int")
        s = str(ptr)
        assert "4096" in s
        render_config.show_addresses_hex = True  # Reset


# ============================================================
# GlobalStaticSegment Tests
# ============================================================

class TestGlobalStaticSegment:
    """Tests for GlobalStaticSegment."""

    def test_empty_segment(self):
        """Test empty global/static segment."""
        segment = GlobalStaticSegment()
        assert len(segment.variables) == 0

    def test_get_variable(self, sample_global):
        """Test getting variable by name."""
        segment = GlobalStaticSegment(variables={sample_global.name: sample_global})
        var = segment.get_variable("g_count")
        assert var is not None
        assert var.value == 42

    def test_get_variable_not_found(self):
        """Test getting non-existent variable."""
        segment = GlobalStaticSegment()
        var = segment.get_variable("nonexistent")
        assert var is None

    def test_get_by_address(self, sample_global):
        """Test getting variable by address."""
        segment = GlobalStaticSegment(variables={sample_global.name: sample_global})
        var = segment.get_by_address(0x4000)
        assert var is not None
        assert var.name == "g_count"

    def test_get_by_address_not_found(self, sample_global):
        """Test getting variable by non-existent address."""
        segment = GlobalStaticSegment(variables={sample_global.name: sample_global})
        var = segment.get_by_address(0x9999)
        assert var is None

    def test_to_console(self, sample_global, sample_static):
        """Test console rendering."""
        segment = GlobalStaticSegment(
            variables={
                sample_global.name: sample_global,
                sample_static.name: sample_static,
            }
        )
        output = segment.to_console()
        assert "g_count" in output
        assert "s_flag" in output


# ============================================================
# HeapSegment Tests
# ============================================================

class TestHeapSegment:
    """Tests for HeapSegment."""

    def test_empty_heap(self):
        """Test empty heap."""
        heap = HeapSegment()
        assert len(heap.blocks) == 0
        assert heap.total_allocated_size() == 0

    def test_get_block(self):
        """Test getting a heap block."""
        block = HeapBlock(0x1000, 4, 100, "int")
        heap = HeapSegment(blocks={0x1000: block})
        retrieved = heap.get_block(0x1000)
        assert retrieved is not None
        assert retrieved.value == 100

    def test_get_all_allocated(self):
        """Test getting all allocated blocks."""
        block1 = HeapBlock(0x1000, 4, 100, "int", is_freed=False)
        block2 = HeapBlock(0x2000, 8, 200, "long", is_freed=True)
        block3 = HeapBlock(0x3000, 4, 300, "int", is_freed=False)
        heap = HeapSegment(blocks={
            0x1000: block1,
            0x2000: block2,
            0x3000: block3,
        })
        allocated = heap.get_all_allocated()
        assert len(allocated) == 2
        assert all(not b.is_freed for b in allocated)

    def test_get_all_freed(self):
        """Test getting all freed blocks."""
        block1 = HeapBlock(0x1000, 4, 100, "int", is_freed=False)
        block2 = HeapBlock(0x2000, 8, 200, "long", is_freed=True)
        heap = HeapSegment(blocks={0x1000: block1, 0x2000: block2})
        freed = heap.get_all_freed()
        assert len(freed) == 1
        assert freed[0].address == 0x2000

    def test_total_allocated_size(self):
        """Test calculating total allocated size."""
        block1 = HeapBlock(0x1000, 4, 100, "int", is_freed=False)
        block2 = HeapBlock(0x2000, 8, 200, "long", is_freed=True)
        block3 = HeapBlock(0x3000, 16, 300, "int", is_freed=False)
        heap = HeapSegment(blocks={
            0x1000: block1,
            0x2000: block2,
            0x3000: block3,
        })
        # Only count non-freed blocks
        assert heap.total_allocated_size() == 20  # 4 + 16

    def test_find_leaks(self):
        """Test finding memory leaks."""
        block1 = HeapBlock(0x1000, 4, 100, "int", is_freed=False)
        block2 = HeapBlock(0x2000, 8, 200, "long", is_freed=False)
        block3 = HeapBlock(0x3000, 4, 300, "int", is_freed=True)
        heap = HeapSegment(blocks={
            0x1000: block1,
            0x2000: block2,
            0x3000: block3,
        })
        # Only block at 0x1000 is reachable
        reachable = {0x1000}
        leaks = heap.find_leaks(reachable)
        assert len(leaks) == 1
        assert leaks[0].address == 0x2000

    def test_to_console(self):
        """Test console rendering."""
        block = HeapBlock(0x1000, 4, 100, "int", allocation_site="main:10")
        heap = HeapSegment(blocks={0x1000: block})
        output = heap.to_console()
        assert "Heap" in output


# ============================================================
# StackFrame Tests
# ============================================================

class TestStackFrame:
    """Tests for StackFrame."""

    def test_empty_frame(self):
        """Test empty stack frame."""
        frame = StackFrame("main")
        assert frame.function_name == "main"
        assert len(frame.locals) == 0
        assert len(frame.parameters) == 0

    def test_get_variable_local(self):
        """Test getting a local variable."""
        frame = StackFrame("main")
        var = StackVariable("x", 0x7000, 10, "int")
        frame.locals["x"] = var
        retrieved = frame.get_variable("x")
        assert retrieved is not None
        assert retrieved.value == 10

    def test_get_variable_parameter(self):
        """Test getting a parameter."""
        frame = StackFrame("foo")
        param = StackVariable("arg", 0x7000, 5, "int")
        frame.parameters["arg"] = param
        retrieved = frame.get_variable("arg")
        assert retrieved is not None
        assert retrieved.value == 5

    def test_get_variable_priority(self):
        """Test that parameters take priority over locals."""
        frame = StackFrame("foo")
        param = StackVariable("x", 0x7000, 5, "int")
        local = StackVariable("x", 0x7008, 10, "int")
        frame.parameters["x"] = param
        frame.locals["x"] = local
        retrieved = frame.get_variable("x")
        assert retrieved.value == 5  # Parameter, not local

    def test_all_variables(self):
        """Test getting all variables."""
        frame = StackFrame("foo")
        param = StackVariable("arg", 0x7000, 5, "int")
        local = StackVariable("x", 0x7008, 10, "int")
        frame.parameters["arg"] = param
        frame.locals["x"] = local
        all_vars = frame.all_variables()
        assert len(all_vars) == 2
        assert "arg" in all_vars
        assert "x" in all_vars

    def test_to_console(self):
        """Test console rendering."""
        frame = StackFrame("main")
        var = StackVariable("x", 0x7000, 10, "int")
        frame.locals["x"] = var
        output = frame.to_console()
        assert "main" in output
        assert "x" in output


# ============================================================
# StackSegment Tests
# ============================================================

class TestStackSegment:
    """Tests for StackSegment."""

    def test_empty_stack(self):
        """Test empty stack."""
        stack = StackSegment()
        assert len(stack.frames) == 0
        assert stack.depth() == 0
        assert stack.current_frame() is None

    def test_current_frame(self):
        """Test getting current frame."""
        stack = StackSegment()
        frame1 = StackFrame("main")
        frame2 = StackFrame("foo")
        stack.frames.append(frame1)
        stack.frames.append(frame2)
        current = stack.current_frame()
        assert current is not None
        assert current.function_name == "foo"

    def test_find_variable(self):
        """Test finding a variable in stack."""
        stack = StackSegment()
        frame1 = StackFrame("main")
        frame1.locals["x"] = StackVariable("x", 0x7000, 10, "int")
        frame2 = StackFrame("foo")
        frame2.locals["y"] = StackVariable("y", 0x7008, 20, "int")
        stack.frames.append(frame1)
        stack.frames.append(frame2)

        # Find in current frame
        result = stack.find_variable("y")
        assert result is not None
        frame_idx, var = result
        assert frame_idx == 1
        assert var.value == 20

        # Find in previous frame
        result = stack.find_variable("x")
        assert result is not None
        frame_idx, var = result
        assert frame_idx == 0
        assert var.value == 10

    def test_find_variable_not_found(self):
        """Test finding non-existent variable."""
        stack = StackSegment()
        stack.frames.append(StackFrame("main"))
        result = stack.find_variable("nonexistent")
        assert result is None

    def test_depth(self):
        """Test stack depth."""
        stack = StackSegment()
        assert stack.depth() == 0
        stack.frames.append(StackFrame("main"))
        assert stack.depth() == 1
        stack.frames.append(StackFrame("foo"))
        assert stack.depth() == 2

    def test_to_console(self):
        """Test console rendering."""
        stack = StackSegment()
        frame = StackFrame("main")
        stack.frames.append(frame)
        output = stack.to_console()
        assert "Stack" in output
        assert "main" in output


# ============================================================
# CpuState Tests
# ============================================================

class TestCpuState:
    """Tests for CpuState."""

    def test_default_cpu_state(self):
        """Test default CPU state."""
        cpu = CpuState()
        assert cpu.pc is None
        assert cpu.sp is None
        assert cpu.bp is None
        assert len(cpu.extra) == 0

    def test_cpu_state_with_values(self):
        """Test CPU state with values."""
        cpu = CpuState(pc=0x400000, sp=0x7fff0000, bp=0x7fff0010)
        assert cpu.pc == 0x400000
        assert cpu.sp == 0x7fff0000
        assert cpu.bp == 0x7fff0010

    def test_cpu_extra_registers(self):
        """Test extra registers."""
        cpu = CpuState(extra={"rax": 10, "rbx": 20})
        assert cpu.extra["rax"] == 10
        assert cpu.extra["rbx"] == 20

    def test_to_console(self):
        """Test console rendering."""
        cpu = CpuState(pc=0x400000, sp=0x7fff0000)
        output = cpu.to_console()
        assert "CPU" in output
        assert "PC" in output


# ============================================================
# MemorySnapshot Tests
# ============================================================

class TestMemorySnapshot:
    """Tests for MemorySnapshot."""

    def test_create_initial_snapshot(self, sample_global):
        """Test creating initial snapshot."""
        snapshot = create_initial_snapshot(
            globals=[sample_global],
            step_id=0,
            description="Initial",
        )
        assert snapshot.step_id == 0
        assert snapshot.description == "Initial"
        assert "g_count" in snapshot.globals_statics.variables
        assert len(snapshot.stack.frames) == 0
        assert len(snapshot.heap.blocks) == 0

    def test_create_initial_snapshot_no_globals(self):
        """Test creating snapshot without globals."""
        snapshot = create_initial_snapshot()
        assert len(snapshot.globals_statics.variables) == 0

    def test_get_value_at_address_global(self, sample_global):
        """Test getting value from global."""
        snapshot = create_initial_snapshot(globals=[sample_global])
        value = snapshot.get_value_at_address(0x4000)
        assert value == 42

    def test_get_value_at_address_not_found(self, basic_snapshot):
        """Test getting value at non-existent address."""
        value = basic_snapshot.get_value_at_address(0x9999)
        assert value is None

    def test_find_all_pointers_to(self, sample_global):
        """Test finding pointers."""
        snapshot = create_initial_snapshot(globals=[sample_global])
        builder = SnapshotBuilder(snapshot)
        builder.push_frame("main")
        builder.set_local("ptr", PointerValue(0x4000, "int"), "int*")
        snapshot2 = builder.build()

        pointers = snapshot2.find_all_pointers_to(0x4000)
        assert len(pointers) == 1
        desc, addr = pointers[0]
        assert "ptr" in desc

    def test_to_console(self, basic_snapshot):
        """Test console rendering."""
        output = basic_snapshot.to_console()
        assert "Step 0" in output
        assert "Test snapshot" in output

    def test_to_console_with_types(self, basic_snapshot, sample_struct):
        """Test console rendering with types."""
        basic_snapshot.types.register_struct(sample_struct)
        output = basic_snapshot.to_console(show_types=True)
        assert "struct Point" in output


# ============================================================
# SnapshotBuilder Tests
# ============================================================

class TestSnapshotBuilder:
    """Tests for SnapshotBuilder."""

    def test_builder_immutability(self, basic_snapshot):
        """Test that builder doesn't modify original snapshot."""
        original_globals = dict(basic_snapshot.globals_statics.variables)
        builder = SnapshotBuilder(basic_snapshot)
        builder.set_global("g_count", 999)
        new_snapshot = builder.build()

        # Original unchanged
        assert basic_snapshot.globals_statics.variables["g_count"].value == 42
        # New snapshot changed
        assert new_snapshot.globals_statics.variables["g_count"].value == 999

    def test_push_pop_frame(self, basic_snapshot):
        """Test pushing and popping frames."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.push_frame("main")
        builder.push_frame("foo")
        snapshot = builder.build()
        assert snapshot.stack.depth() == 2
        assert snapshot.stack.frames[0].function_name == "main"
        assert snapshot.stack.frames[1].function_name == "foo"

        # Pop frame
        builder2 = SnapshotBuilder(snapshot)
        builder2.pop_frame()
        snapshot2 = builder2.build()
        assert snapshot2.stack.depth() == 1
        assert snapshot2.stack.frames[0].function_name == "main"

    def test_pop_frame_empty_stack(self, basic_snapshot):
        """Test popping from empty stack."""
        builder = SnapshotBuilder(basic_snapshot)
        with pytest.raises(RuntimeError, match="stack is empty"):
            builder.pop_frame()

    def test_set_local(self, basic_snapshot):
        """Test setting local variable."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.push_frame("main")
        builder.set_local("x", 10, "int", address=0x7000)
        snapshot = builder.build()

        frame = snapshot.stack.current_frame()
        assert frame is not None
        assert "x" in frame.locals
        assert frame.locals["x"].value == 10

    def test_set_local_no_frame(self, basic_snapshot):
        """Test setting local without frame."""
        builder = SnapshotBuilder(basic_snapshot)
        with pytest.raises(RuntimeError, match="No frame on stack"):
            builder.set_local("x", 10, "int")

    def test_set_local_auto_address(self, basic_snapshot):
        """Test setting local with auto-generated address."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.push_frame("main")
        builder.set_local("x", 10, "int")  # No address
        builder.set_local("y", 20, "int")  # No address
        snapshot = builder.build()

        frame = snapshot.stack.current_frame()
        assert frame is not None
        x_addr = frame.locals["x"].address
        y_addr = frame.locals["y"].address
        assert x_addr != y_addr  # Different addresses

    def test_set_parameter(self, basic_snapshot):
        """Test setting function parameter."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.push_frame("foo")
        builder.set_parameter("arg", 5, "int", address=0x7000)
        snapshot = builder.build()

        frame = snapshot.stack.current_frame()
        assert frame is not None
        assert "arg" in frame.parameters
        assert frame.parameters["arg"].value == 5

    def test_update_local(self, basic_snapshot):
        """Test updating local variable."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.push_frame("main")
        builder.set_local("x", 10, "int")
        builder.update_local("x", 20)
        snapshot = builder.build()

        frame = snapshot.stack.current_frame()
        assert frame.locals["x"].value == 20

    def test_update_local_not_found(self, basic_snapshot):
        """Test updating non-existent local."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.push_frame("main")
        with pytest.raises(RuntimeError, match="not found"):
            builder.update_local("x", 20)

    def test_malloc(self, basic_snapshot):
        """Test heap allocation."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        snapshot = builder.build()

        block = snapshot.heap.get_block(0x1000)
        assert block is not None
        assert block.size == 4
        assert block.value == 100
        assert not block.is_freed

    def test_malloc_auto_address(self, basic_snapshot):
        """Test malloc with auto-generated address."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr1 = builder.malloc(4, "int", 100)
        builder, addr2 = builder.malloc(4, "int", 200)
        snapshot = builder.build()

        assert addr1 != addr2
        assert snapshot.heap.get_block(addr1) is not None
        assert snapshot.heap.get_block(addr2) is not None

    def test_malloc_duplicate_address(self, basic_snapshot):
        """Test malloc with duplicate address."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        with pytest.raises(ValueError, match="already allocated"):
            builder.malloc(4, "int", 200, address=0x1000)

    def test_free(self, basic_snapshot):
        """Test freeing heap block."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        builder.free(0x1000)
        snapshot = builder.build()

        block = snapshot.heap.get_block(0x1000)
        assert block is not None
        assert block.is_freed

    def test_free_not_found(self, basic_snapshot):
        """Test freeing non-existent block."""
        builder = SnapshotBuilder(basic_snapshot)
        with pytest.raises(KeyError):
            builder.free(0x9999)

    def test_double_free(self, basic_snapshot):
        """Test double free detection."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        builder.free(0x1000)
        with pytest.raises(ValueError, match="Double free"):
            builder.free(0x1000)

    def test_write_heap(self, basic_snapshot):
        """Test writing to heap."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        builder.write_heap(0x1000, 200)
        snapshot = builder.build()

        block = snapshot.heap.get_block(0x1000)
        assert block.value == 200

    def test_write_heap_not_found(self, basic_snapshot):
        """Test writing to non-existent heap block."""
        builder = SnapshotBuilder(basic_snapshot)
        with pytest.raises(KeyError):
            builder.write_heap(0x9999, 100)

    def test_write_heap_freed_memory(self, basic_snapshot):
        """Test writing to freed memory."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        builder.free(0x1000)
        with pytest.raises(ValueError, match="freed memory"):
            builder.write_heap(0x1000, 200)

    def test_read_heap(self, basic_snapshot):
        """Test reading from heap."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        value = builder.read_heap(0x1000)
        assert value == 100

    def test_read_heap_not_found(self, basic_snapshot):
        """Test reading from non-existent heap block."""
        builder = SnapshotBuilder(basic_snapshot)
        with pytest.raises(KeyError):
            builder.read_heap(0x9999)

    def test_read_heap_freed_memory(self, basic_snapshot):
        """Test reading from freed memory."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100, address=0x1000)
        builder.free(0x1000)
        with pytest.raises(ValueError, match="freed memory"):
            builder.read_heap(0x1000)

    def test_set_global(self, basic_snapshot):
        """Test setting global variable."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.set_global("g_count", 999)
        snapshot = builder.build()

        var = snapshot.globals_statics.get_variable("g_count")
        assert var.value == 999

    def test_set_global_not_found(self, basic_snapshot):
        """Test setting non-existent global."""
        builder = SnapshotBuilder(basic_snapshot)
        with pytest.raises(KeyError):
            builder.set_global("nonexistent", 100)

    def test_add_global(self, basic_snapshot):
        """Test adding new global variable."""
        builder = SnapshotBuilder(basic_snapshot)
        new_var = GlobalStaticVariable(
            name="new_global",
            address=0x5000,
            value=77,
            type_name="int",
            storage_class=VariableStorageClass.GLOBAL,
            section=".data",
        )
        builder.add_global(new_var)
        snapshot = builder.build()

        var = snapshot.globals_statics.get_variable("new_global")
        assert var is not None
        assert var.value == 77

    def test_set_cpu_registers(self, basic_snapshot):
        """Test setting CPU registers."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.set_pc(0x400000)
        builder.set_sp(0x7fff0000)
        builder.set_bp(0x7fff0010)
        snapshot = builder.build()

        assert snapshot.cpu is not None
        assert snapshot.cpu.pc == 0x400000
        assert snapshot.cpu.sp == 0x7fff0000
        assert snapshot.cpu.bp == 0x7fff0010

    def test_set_step(self, basic_snapshot):
        """Test setting step metadata."""
        builder = SnapshotBuilder(basic_snapshot)
        builder.set_step(5, "After loop iteration")
        snapshot = builder.build()

        assert snapshot.step_id == 5
        assert snapshot.description == "After loop iteration"

    def test_build_auto_increment_step(self, basic_snapshot):
        """Test auto-incrementing step ID."""
        builder = SnapshotBuilder(basic_snapshot)
        snapshot = builder.build()
        assert snapshot.step_id == basic_snapshot.step_id + 1

    def test_chaining(self, basic_snapshot):
        """Test method chaining."""
        snapshot = (
            SnapshotBuilder(basic_snapshot)
            .push_frame("main")
            .set_local("x", 10, "int")
            .set_global("g_count", 100)
            .set_step(1, "Test")
            .build()
        )

        assert snapshot.stack.depth() == 1
        assert snapshot.stack.current_frame().locals["x"].value == 10
        assert snapshot.globals_statics.get_variable("g_count").value == 100
        assert snapshot.step_id == 1


# ============================================================
# Utility Function Tests
# ============================================================

class TestDiffSnapshots:
    """Tests for diff_snapshots utility."""

    def test_diff_no_changes(self, basic_snapshot):
        """Test diff with no changes."""
        snapshot2 = SnapshotBuilder(basic_snapshot).build()
        diff = diff_snapshots(basic_snapshot, snapshot2)
        assert "no changes" in diff.lower()

    def test_diff_global_change(self, basic_snapshot):
        """Test diff with global variable change."""
        snapshot2 = (
            SnapshotBuilder(basic_snapshot)
            .set_global("g_count", 999)
            .build()
        )
        diff = diff_snapshots(basic_snapshot, snapshot2)
        assert "g_count" in diff
        assert "42" in diff
        assert "999" in diff

    def test_diff_stack_push(self, basic_snapshot):
        """Test diff with stack frame push."""
        snapshot2 = (
            SnapshotBuilder(basic_snapshot)
            .push_frame("main")
            .build()
        )
        diff = diff_snapshots(basic_snapshot, snapshot2)
        assert "Pushed frame" in diff
        assert "main" in diff

    def test_diff_heap_allocation(self, basic_snapshot):
        """Test diff with heap allocation."""
        builder = SnapshotBuilder(basic_snapshot)
        builder, addr = builder.malloc(4, "int", 100)
        snapshot2 = builder.build()
        diff = diff_snapshots(basic_snapshot, snapshot2)
        assert "Allocated" in diff
        assert "4 bytes" in diff


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_simple_program_flow(self):
        """Test simulating a simple program."""
        # Step 0: Initial state
        g = GlobalStaticVariable(
            name="counter",
            address=0x4000,
            value=0,
            type_name="int",
            storage_class=VariableStorageClass.GLOBAL,
            section=".data",
        )
        snapshot0 = create_initial_snapshot(globals=[g])

        # Step 1: Enter main, declare local
        snapshot1 = (
            SnapshotBuilder(snapshot0)
            .push_frame("main")
            .set_local("x", 10, "int")
            .set_step(1, "int x = 10")
            .build()
        )
        assert snapshot1.stack.depth() == 1
        assert snapshot1.stack.current_frame().locals["x"].value == 10

        # Step 2: Allocate on heap
        builder = SnapshotBuilder(snapshot1)
        builder, heap_addr = builder.malloc(4, "int", 0)
        snapshot2 = (
            builder
            .set_local("ptr", PointerValue(heap_addr, "int"), "int*")
            .set_step(2, "int* ptr = malloc(sizeof(int))")
            .build()
        )
        assert len(snapshot2.heap.blocks) == 1
        ptr_var = snapshot2.stack.current_frame().locals["ptr"]
        assert isinstance(ptr_var.value, PointerValue)

        # Step 3: Write to heap
        snapshot3 = (
            SnapshotBuilder(snapshot2)
            .write_heap(heap_addr, 42)
            .set_step(3, "*ptr = 42")
            .build()
        )
        assert snapshot3.heap.get_block(heap_addr).value == 42

        # Step 4: Free memory
        snapshot4 = (
            SnapshotBuilder(snapshot3)
            .free(heap_addr)
            .set_step(4, "free(ptr)")
            .build()
        )
        assert snapshot4.heap.get_block(heap_addr).is_freed

        # Step 5: Return from main
        snapshot5 = (
            SnapshotBuilder(snapshot4)
            .pop_frame()
            .set_step(5, "return 0")
            .build()
        )
        assert snapshot5.stack.depth() == 0

    def test_nested_function_calls(self):
        """Test nested function calls with parameters."""
        snapshot0 = create_initial_snapshot()

        # main()
        snapshot1 = (
            SnapshotBuilder(snapshot0)
            .push_frame("main")
            .set_local("a", 5, "int")
            .set_step(1, "In main")
            .build()
        )

        # foo(a)
        snapshot2 = (
            SnapshotBuilder(snapshot1)
            .push_frame("foo")
            .set_parameter("x", 5, "int")
            .set_local("result", 10, "int")
            .set_step(2, "In foo")
            .build()
        )
        assert snapshot2.stack.depth() == 2

        # Return from foo
        snapshot3 = (
            SnapshotBuilder(snapshot2)
            .pop_frame()
            .update_local("a", 10)  # Update with return value
            .set_step(3, "After foo returns")
            .build()
        )
        assert snapshot3.stack.depth() == 1
        assert snapshot3.stack.current_frame().locals["a"].value == 10

    def test_memory_leak_detection(self):
        """Test detecting memory leaks."""
        snapshot0 = create_initial_snapshot()

        # Allocate two blocks
        builder = SnapshotBuilder(snapshot0)
        builder.push_frame("main")
        builder, addr1 = builder.malloc(4, "int", 100)
        builder, addr2 = builder.malloc(4, "int", 200)
        builder.set_local("ptr1", PointerValue(addr1, "int"), "int*")
        # Note: ptr2 not stored, so addr2 is leaked
        snapshot1 = builder.build()

        # Find leaks (only addr1 is reachable via ptr1)
        reachable = {addr1}
        leaks = snapshot1.heap.find_leaks(reachable)
        assert len(leaks) == 1
        assert leaks[0].address == addr2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
