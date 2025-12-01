"""
gui_demo.py

Demonstration of the Memory Visualizer GUI with a complete C program simulation.

This script creates a series of memory snapshots representing the execution
of a C program and displays them in the GUI.
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
)
from memory_gui import visualize_snapshots


def create_demo_snapshots():
    """Create a series of snapshots demonstrating various memory operations."""

    snapshots = []

    # Define types
    types = TypeRegistry()
    node_struct = StructDescriptor(
        name="Node",
        fields=[
            FieldDescriptor("data", "int", 0),
            FieldDescriptor("next", "struct Node*", 8),
        ],
        size=16,
    )
    types.register_struct(node_struct)

    # Step 0: Initial state with globals
    print("Creating snapshots for visualization...")

    g_count = GlobalStaticVariable(
        name="g_count",
        address=0x4000,
        value=0,
        type_name="int",
        storage_class=VariableStorageClass.GLOBAL,
        section=".data",
    )

    g_max = GlobalStaticVariable(
        name="g_max",
        address=0x4008,
        value=100,
        type_name="int",
        storage_class=VariableStorageClass.GLOBAL,
        section=".data",
    )

    snapshot0 = create_initial_snapshot(
        globals=[g_count, g_max],
        types=types,
        step_id=0,
        description="Program initialization"
    )
    snapshots.append(snapshot0)
    print(f"  Step 0: {snapshot0.description}")

    # Step 1: Enter main()
    snapshot1 = (
        SnapshotBuilder(snapshot0)
        .push_frame("main")
        .set_step(1, "Entered main()")
        .build()
    )
    snapshots.append(snapshot1)
    print(f"  Step 1: {snapshot1.description}")

    # Step 2: Declare local variables
    snapshot2 = (
        SnapshotBuilder(snapshot1)
        .set_local("x", 10, "int", address=0x7fff_0000)
        .set_local("y", 20, "int", address=0x7fff_0008)
        .set_local("sum", 0, "int", address=0x7fff_0010)
        .set_step(2, "Declared local variables x, y, sum")
        .build()
    )
    snapshots.append(snapshot2)
    print(f"  Step 2: {snapshot2.description}")

    # Step 3: Allocate first Node
    builder3 = SnapshotBuilder(snapshot2)
    builder3, node1_addr = builder3.malloc(
        16,
        "struct Node",
        {"data": 0, "next": None},
        allocation_site="main:10"
    )
    snapshot3 = (
        builder3
        .set_local("head", PointerValue(node1_addr, "struct Node"), "struct Node*", address=0x7fff_0018)
        .set_step(3, "Allocated first Node (head)")
        .build()
    )
    snapshots.append(snapshot3)
    print(f"  Step 3: {snapshot3.description}")

    # Step 4: Initialize first node
    snapshot4 = (
        SnapshotBuilder(snapshot3)
        .write_heap(node1_addr, {"data": 10, "next": None})
        .set_step(4, "Initialized head->data = 10")
        .build()
    )
    snapshots.append(snapshot4)
    print(f"  Step 4: {snapshot4.description}")

    # Step 5: Allocate second Node
    builder5 = SnapshotBuilder(snapshot4)
    builder5, node2_addr = builder5.malloc(
        16,
        "struct Node",
        {"data": 0, "next": None},
        allocation_site="main:15"
    )
    snapshot5 = (
        builder5
        .set_local("second", PointerValue(node2_addr, "struct Node"), "struct Node*", address=0x7fff_0020)
        .set_step(5, "Allocated second Node")
        .build()
    )
    snapshots.append(snapshot5)
    print(f"  Step 5: {snapshot5.description}")

    # Step 6: Initialize second node and link it
    snapshot6 = (
        SnapshotBuilder(snapshot5)
        .write_heap(node2_addr, {"data": 20, "next": None})
        .write_heap(node1_addr, {"data": 10, "next": PointerValue(node2_addr, "struct Node")})
        .set_step(6, "Linked head->next = second, second->data = 20")
        .build()
    )
    snapshots.append(snapshot6)
    print(f"  Step 6: {snapshot6.description}")

    # Step 7: Call a function
    snapshot7 = (
        SnapshotBuilder(snapshot6)
        .push_frame("calculate_sum", return_address=0x400150)
        .set_parameter("a", 10, "int", address=0x7fff_0100)
        .set_parameter("b", 20, "int", address=0x7fff_0108)
        .set_step(7, "Called calculate_sum(x, y)")
        .build()
    )
    snapshots.append(snapshot7)
    print(f"  Step 7: {snapshot7.description}")

    # Step 8: Compute in function
    snapshot8 = (
        SnapshotBuilder(snapshot7)
        .set_local("result", 30, "int", address=0x7fff_0110)
        .set_step(8, "Computing result = a + b in calculate_sum")
        .build()
    )
    snapshots.append(snapshot8)
    print(f"  Step 8: {snapshot8.description}")

    # Step 9: Return from function
    snapshot9 = (
        SnapshotBuilder(snapshot8)
        .pop_frame()
        .update_local("sum", 30)
        .set_step(9, "Returned from calculate_sum, sum = 30")
        .build()
    )
    snapshots.append(snapshot9)
    print(f"  Step 9: {snapshot9.description}")

    # Step 10: Update global counter
    snapshot10 = (
        SnapshotBuilder(snapshot9)
        .set_global("g_count", 2)
        .set_step(10, "Incremented g_count to 2")
        .build()
    )
    snapshots.append(snapshot10)
    print(f"  Step 10: {snapshot10.description}")

    # Step 11: Allocate third node
    builder11 = SnapshotBuilder(snapshot10)
    builder11, node3_addr = builder11.malloc(
        16,
        "struct Node",
        {"data": 30, "next": None},
        allocation_site="main:25"
    )
    snapshot11 = (
        builder11
        .set_local("third", PointerValue(node3_addr, "struct Node"), "struct Node*", address=0x7fff_0028)
        .write_heap(node2_addr, {"data": 20, "next": PointerValue(node3_addr, "struct Node")})
        .set_step(11, "Allocated and linked third node")
        .build()
    )
    snapshots.append(snapshot11)
    print(f"  Step 11: {snapshot11.description}")

    # Step 12: Free first node
    snapshot12 = (
        SnapshotBuilder(snapshot11)
        .free(node1_addr)
        .set_step(12, "Freed head node")
        .build()
    )
    snapshots.append(snapshot12)
    print(f"  Step 12: {snapshot12.description}")

    # Step 13: Update head pointer
    snapshot13 = (
        SnapshotBuilder(snapshot12)
        .update_local("head", PointerValue(node2_addr, "struct Node"))
        .set_step(13, "Updated head to point to second node")
        .build()
    )
    snapshots.append(snapshot13)
    print(f"  Step 13: {snapshot13.description}")

    # Step 14: Free all remaining nodes
    snapshot14 = (
        SnapshotBuilder(snapshot13)
        .free(node2_addr)
        .free(node3_addr)
        .set_step(14, "Freed all remaining nodes")
        .build()
    )
    snapshots.append(snapshot14)
    print(f"  Step 14: {snapshot14.description}")

    # Step 15: Return from main
    snapshot15 = (
        SnapshotBuilder(snapshot14)
        .pop_frame()
        .set_step(15, "Exited main(), program complete")
        .build()
    )
    snapshots.append(snapshot15)
    print(f"  Step 15: {snapshot15.description}")

    print(f"\nCreated {len(snapshots)} snapshots")
    return snapshots


def main():
    """Run the GUI demo."""
    print("=" * 70)
    print("Memory Visualizer GUI Demo")
    print("=" * 70)
    print()
    print("This demo simulates a C program that:")
    print("  - Uses global variables")
    print("  - Allocates a linked list on the heap")
    print("  - Calls functions with parameters")
    print("  - Manipulates pointers")
    print("  - Frees memory")
    print()
    print("Controls:")
    print("  - Use the toolbar buttons to navigate between steps")
    print("  - Use the slider to jump to any step")
    print("  - Click on memory items to see details")
    print("  - Use 'Export Image' to save the visualization")
    print()

    # Create snapshots
    snapshots = create_demo_snapshots()

    print()
    print("=" * 70)
    print("Launching GUI...")
    print("=" * 70)
    print()

    # Launch GUI
    visualize_snapshots(snapshots)


if __name__ == "__main__":
    main()
