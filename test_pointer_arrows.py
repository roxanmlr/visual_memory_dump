"""
test_pointer_arrows.py

Test script to verify pointer arrow visualization works correctly.
This creates a scenario with various pointer types and visualizes them.
"""

from memory_model import (
    create_initial_snapshot,
    SnapshotBuilder,
    GlobalStaticVariable,
    VariableStorageClass,
    PointerValue,
)
from memory_gui import visualize_snapshots


def create_pointer_test_snapshots():
    """Create snapshots demonstrating pointer arrows."""
    snapshots = []

    # Step 0: Initial state with global pointer
    g_ptr = GlobalStaticVariable(
        name="g_ptr",
        address=0x4000,
        value=PointerValue(0, "int", is_null=True),  # NULL initially
        type_name="int*",
        storage_class=VariableStorageClass.GLOBAL,
        section=".data",
    )

    snapshot0 = create_initial_snapshot(
        globals=[g_ptr],
        step_id=0,
        description="Initial state with global pointer"
    )
    snapshots.append(snapshot0)

    # Step 1: Allocate heap and point global to it
    builder1 = SnapshotBuilder(snapshot0)
    builder1, heap_addr1 = builder1.malloc(4, "int", 42, allocation_site="test:10")
    snapshot1 = (
        builder1
        .set_global("g_ptr", PointerValue(heap_addr1, "int"))
        .set_step(1, f"Global pointer → heap @ {hex(heap_addr1)}")
        .build()
    )
    snapshots.append(snapshot1)

    # Step 2: Create stack with local pointer to same heap
    snapshot2 = (
        SnapshotBuilder(snapshot1)
        .push_frame("main")
        .set_local("x", 10, "int", address=0x7fff_0000)
        .set_local("ptr", PointerValue(heap_addr1, "int"), "int*", address=0x7fff_0008)
        .set_step(2, "Stack pointer also → heap (multiple arrows)")
        .build()
    )
    snapshots.append(snapshot2)

    # Step 3: Allocate second heap block
    builder3 = SnapshotBuilder(snapshot2)
    builder3, heap_addr2 = builder3.malloc(4, "int", 100, allocation_site="test:15")
    snapshot3 = (
        builder3
        .set_local("ptr2", PointerValue(heap_addr2, "int"), "int*", address=0x7fff_0010)
        .set_step(3, f"Second pointer → second heap @ {hex(heap_addr2)}")
        .build()
    )
    snapshots.append(snapshot3)

    # Step 4: Create linked list - heap pointing to heap
    builder4 = SnapshotBuilder(snapshot3)
    builder4, node1_addr = builder4.malloc(16, "struct Node", {"data": 10, "next": PointerValue(0, "struct Node", is_null=True)}, allocation_site="test:20")
    builder4, node2_addr = builder4.malloc(16, "struct Node", {"data": 20, "next": PointerValue(0, "struct Node", is_null=True)}, allocation_site="test:21")
    snapshot4 = (
        builder4
        .write_heap(node1_addr, {"data": 10, "next": PointerValue(node2_addr, "struct Node")})
        .set_local("head", PointerValue(node1_addr, "struct Node"), "struct Node*", address=0x7fff_0018)
        .set_step(4, f"Linked list: stack → heap → heap")
        .build()
    )
    snapshots.append(snapshot4)

    # Step 5: Add third node in chain
    builder5 = SnapshotBuilder(snapshot4)
    builder5, node3_addr = builder5.malloc(16, "struct Node", {"data": 30, "next": PointerValue(0, "struct Node", is_null=True)}, allocation_site="test:25")
    snapshot5 = (
        builder5
        .write_heap(node2_addr, {"data": 20, "next": PointerValue(node3_addr, "struct Node")})
        .set_step(5, f"Longer chain: stack → heap → heap → heap")
        .build()
    )
    snapshots.append(snapshot5)

    return snapshots


def main():
    """Run the pointer arrow test."""
    print("=" * 70)
    print("Pointer Arrow Visualization Test")
    print("=" * 70)
    print()
    print("This test demonstrates:")
    print("  1. Global pointer → Heap")
    print("  2. Stack pointer → Heap")
    print("  3. Multiple pointers → Same heap block")
    print("  4. Heap → Heap (linked list)")
    print("  5. Chained pointers")
    print()
    print("You should see RED ARROWS connecting:")
    print("  - Pointer variables to their target addresses")
    print("  - Multiple arrows for shared targets")
    print("  - Arrow chains for linked structures")
    print()
    print("=" * 70)
    print()

    snapshots = create_pointer_test_snapshots()
    print(f"Created {len(snapshots)} test snapshots")
    print("Launching visualization GUI...")
    print()

    visualize_snapshots(snapshots)


if __name__ == "__main__":
    main()
