"""
example_usage.py

Comprehensive example demonstrating the memory_model library features.
This script simulates a C program with multiple functions, heap allocations,
and demonstrates various library capabilities.
"""

from memory_model import (
    create_initial_snapshot,
    SnapshotBuilder,
    GlobalStaticVariable,
    VariableStorageClass,
    PointerValue,
    TypeRegistry,
    StructDescriptor,
    FieldDescriptor,
    diff_snapshots,
    render_config,
)


def main():
    """Run comprehensive example."""
    print("=" * 70)
    print("Memory Model Library - Comprehensive Example")
    print("=" * 70)
    print()

    # Configure rendering
    render_config.pointer_arrow = "→"
    render_config.show_addresses_hex = True

    # Create type registry
    types = TypeRegistry()

    # Define Point struct
    point_struct = StructDescriptor(
        name="Point",
        fields=[
            FieldDescriptor("x", "int", 0),
            FieldDescriptor("y", "int", 4),
        ],
        size=8,
    )
    types.register_struct(point_struct)

    # Define Node struct (for linked list)
    node_struct = StructDescriptor(
        name="Node",
        fields=[
            FieldDescriptor("data", "int", 0),
            FieldDescriptor("next", "struct Node*", 8),
        ],
        size=16,
    )
    types.register_struct(node_struct)

    print("=" * 70)
    print("Simulating C Program:")
    print("=" * 70)
    print("""
int g_counter = 0;

struct Point { int x; int y; };
struct Node { int data; struct Node* next; };

int calculate(int a, int b) {
    int result = a + b;
    return result;
}

int main() {
    int x = 10;
    int y = 20;

    // Allocate Point on heap
    struct Point* p = malloc(sizeof(struct Point));
    p->x = 5;
    p->y = 15;

    // Call calculate
    int sum = calculate(x, y);
    g_counter++;

    free(p);
    return 0;
}
    """)
    print("=" * 70)
    print()

    # Step 0: Initial state
    print("Creating initial state...")
    g_counter = GlobalStaticVariable(
        name="g_counter",
        address=0x4000,
        value=0,
        type_name="int",
        storage_class=VariableStorageClass.GLOBAL,
        section=".data",
    )

    snapshot0 = create_initial_snapshot(
        globals=[g_counter],
        types=types,
        step_id=0,
        description="Program start"
    )
    snapshot0.print(show_types=True)
    print("\n" + "=" * 70 + "\n")

    # Step 1: Enter main()
    print("Step 1: Entering main()...")
    snapshot1 = (
        SnapshotBuilder(snapshot0)
        .push_frame("main")
        .set_step(1, "Entered main()")
        .build()
    )
    snapshot1.print()
    print("\n" + "=" * 70 + "\n")

    # Step 2: int x = 10; int y = 20;
    print("Step 2: Declaring local variables...")
    snapshot2 = (
        SnapshotBuilder(snapshot1)
        .set_local("x", 10, "int", address=0x7fff_0000)
        .set_local("y", 20, "int", address=0x7fff_0008)
        .set_step(2, "int x = 10; int y = 20;")
        .build()
    )
    snapshot2.print()
    print("\n" + "=" * 70 + "\n")

    # Step 3: Allocate Point on heap
    print("Step 3: Allocating struct Point on heap...")
    builder3 = SnapshotBuilder(snapshot2)
    builder3, point_addr = builder3.malloc(
        8,
        "struct Point",
        {"x": 0, "y": 0},
        allocation_site="main:15"
    )
    snapshot3 = (
        builder3
        .set_local("p", PointerValue(point_addr, "struct Point"), "struct Point*", address=0x7fff_0010)
        .set_step(3, "struct Point* p = malloc(sizeof(struct Point));")
        .build()
    )
    snapshot3.print()
    print("\n" + "=" * 70 + "\n")

    # Step 4: p->x = 5; p->y = 15;
    print("Step 4: Initializing Point fields...")
    snapshot4 = (
        SnapshotBuilder(snapshot3)
        .write_heap(point_addr, {"x": 5, "y": 15})
        .set_step(4, "p->x = 5; p->y = 15;")
        .build()
    )
    snapshot4.print()
    print("\n" + "=" * 70 + "\n")

    # Step 5: Call calculate(x, y)
    print("Step 5: Calling calculate(10, 20)...")
    snapshot5 = (
        SnapshotBuilder(snapshot4)
        .push_frame("calculate", return_address=0x400150)
        .set_parameter("a", 10, "int", address=0x7fff_0020)
        .set_parameter("b", 20, "int", address=0x7fff_0028)
        .set_step(5, "Call calculate(x, y)")
        .build()
    )
    snapshot5.print()
    print("\n" + "=" * 70 + "\n")

    # Step 6: int result = a + b; (in calculate)
    print("Step 6: Computing result in calculate()...")
    snapshot6 = (
        SnapshotBuilder(snapshot5)
        .set_local("result", 30, "int", address=0x7fff_0030)
        .set_step(6, "int result = a + b;")
        .build()
    )
    snapshot6.print()
    print("\n" + "=" * 70 + "\n")

    # Step 7: Return from calculate
    print("Step 7: Returning from calculate()...")
    snapshot7 = (
        SnapshotBuilder(snapshot6)
        .pop_frame()
        .set_local("sum", 30, "int", address=0x7fff_0018)
        .set_step(7, "int sum = calculate(x, y); // returned 30")
        .build()
    )
    snapshot7.print()
    print("\n" + "=" * 70 + "\n")

    # Step 8: g_counter++
    print("Step 8: Incrementing global counter...")
    snapshot8 = (
        SnapshotBuilder(snapshot7)
        .set_global("g_counter", 1)
        .set_step(8, "g_counter++;")
        .build()
    )
    snapshot8.print()
    print("\n" + "=" * 70 + "\n")

    # Step 9: free(p)
    print("Step 9: Freeing heap memory...")
    snapshot9 = (
        SnapshotBuilder(snapshot8)
        .free(point_addr)
        .set_step(9, "free(p);")
        .build()
    )
    snapshot9.print()
    print("\n" + "=" * 70 + "\n")

    # Step 10: return 0
    print("Step 10: Returning from main()...")
    snapshot10 = (
        SnapshotBuilder(snapshot9)
        .pop_frame()
        .set_step(10, "return 0;")
        .build()
    )
    snapshot10.print()
    print("\n" + "=" * 70 + "\n")

    # Demonstrate diffing
    print("=" * 70)
    print("Demonstrating Snapshot Diff (Step 7 -> Step 8):")
    print("=" * 70)
    print(diff_snapshots(snapshot7, snapshot8))
    print("\n" + "=" * 70 + "\n")

    # Demonstrate pointer finding
    print("=" * 70)
    print("Finding all pointers to heap allocation:")
    print("=" * 70)
    pointers = snapshot4.find_all_pointers_to(point_addr)
    if pointers:
        for desc, addr in pointers:
            print(f"  {desc} @ {hex(addr)}")
    else:
        print("  (no pointers found)")
    print("\n" + "=" * 70 + "\n")

    # Demonstrate memory analysis
    print("=" * 70)
    print("Memory Analysis at Step 4:")
    print("=" * 70)
    print(f"Stack depth: {snapshot4.stack.depth()} frame(s)")
    print(f"Heap allocations: {len(snapshot4.heap.get_all_allocated())} block(s)")
    print(f"Total heap size: {snapshot4.heap.total_allocated_size()} bytes")
    print(f"Global variables: {len(snapshot4.globals_statics.variables)}")
    print("\n" + "=" * 70 + "\n")

    # Demonstrate memory leak detection
    print("=" * 70)
    print("Memory Leak Detection Example:")
    print("=" * 70)
    print("Creating scenario with leaked memory...")

    # Create snapshot with multiple allocations
    builder_leak = SnapshotBuilder(snapshot2)
    builder_leak, addr1 = builder_leak.malloc(4, "int", 100, allocation_site="main:20")
    builder_leak, addr2 = builder_leak.malloc(4, "int", 200, allocation_site="main:21")
    builder_leak.set_local("ptr1", PointerValue(addr1, "int"), "int*")
    # Note: addr2 is not stored anywhere, so it's leaked
    snapshot_leak = builder_leak.build()

    # Find reachable addresses (only addr1 via ptr1)
    reachable = {addr1}
    leaks = snapshot_leak.heap.find_leaks(reachable)

    print(f"Total allocations: {len(snapshot_leak.heap.blocks)}")
    print(f"Reachable: {len(reachable)}")
    print(f"Leaked: {len(leaks)}")
    if leaks:
        for leak in leaks:
            print(f"  - Leaked block at {hex(leak.address)}: {leak.size} bytes ({leak.type_name})")
            if leak.allocation_site:
                print(f"    Allocated at: {leak.allocation_site}")
    print("\n" + "=" * 70 + "\n")

    print("Example complete!")


if __name__ == "__main__":
    main()
