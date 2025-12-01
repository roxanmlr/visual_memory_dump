"""
visual_arrow_test.py

Simple visual test to verify pointer arrows are rendering correctly.
This creates an obvious scenario with clear pointer relationships.
"""

from memory_model import (
    create_initial_snapshot,
    SnapshotBuilder,
    GlobalStaticVariable,
    VariableStorageClass,
    PointerValue,
)
from memory_gui import MemoryVisualizer
import tkinter as tk


def create_simple_pointer_scenario():
    """Create a very simple scenario with obvious pointers."""

    # Step 1: Just a stack pointer to heap
    snapshot0 = create_initial_snapshot(step_id=0, description="Initial empty state")

    # Step 2: Allocate heap and create pointer
    builder = SnapshotBuilder(snapshot0)
    builder.push_frame("main")
    builder, heap_addr = builder.malloc(4, "int", 42, allocation_site="line 10")

    print(f"\n{'='*70}")
    print(f"HEAP ADDRESS ALLOCATED: {hex(heap_addr)}")
    print(f"{'='*70}\n")

    snapshot1 = (
        builder
        .set_local("ptr", PointerValue(heap_addr, "int"), "int*")
        .set_step(1, f"Stack pointer → Heap at {hex(heap_addr)}")
        .build()
    )

    # Step 3: Add another pointer to same location
    snapshot2 = (
        SnapshotBuilder(snapshot1)
        .set_local("ptr2", PointerValue(heap_addr, "int"), "int*")
        .set_step(2, f"TWO pointers → Same heap location")
        .build()
    )

    # Step 4: Create linked list
    builder3 = SnapshotBuilder(snapshot2)
    builder3, node1 = builder3.malloc(8, "Node", {"data": 10, "next": PointerValue(0, "Node", is_null=True)})
    builder3, node2 = builder3.malloc(8, "Node", {"data": 20, "next": PointerValue(0, "Node", is_null=True)})

    print(f"NODE 1 ADDRESS: {hex(node1)}")
    print(f"NODE 2 ADDRESS: {hex(node2)}\n")

    snapshot3 = (
        builder3
        .write_heap(node1, {"data": 10, "next": PointerValue(node2, "Node")})
        .set_local("head", PointerValue(node1, "Node"), "Node*")
        .set_step(3, "Linked list: head → node1 → node2")
        .build()
    )

    return [snapshot0, snapshot1, snapshot2, snapshot3]


def main():
    """Run visual arrow test with debug info."""
    print("="*70)
    print("VISUAL POINTER ARROW TEST")
    print("="*70)
    print()
    print("This test creates clear pointer scenarios.")
    print()
    print("YOU SHOULD SEE:")
    print("  1. Step 1: RED ARROW from 'ptr' (stack) to heap block")
    print("  2. Step 2: TWO RED ARROWS from ptr & ptr2 to same heap block")
    print("  3. Step 3: RED ARROWS showing linked list chain")
    print()
    print("If you DON'T see red arrows, there's an issue!")
    print()

    snapshots = create_simple_pointer_scenario()

    print("="*70)
    print("DEBUG: Checking snapshot 1 for pointers...")
    print("="*70)

    snapshot = snapshots[1]

    # Check if pointers exist
    print(f"\nStack frames: {len(snapshot.stack.frames)}")
    if snapshot.stack.frames:
        frame = snapshot.stack.frames[0]
        print(f"Locals in frame: {list(frame.locals.keys())}")
        for name, var in frame.locals.items():
            print(f"  {name}: type={var.type_name}, value={var.value}")
            if isinstance(var.value, PointerValue):
                print(f"    ✓ IS POINTER! Points to {hex(var.value.address)}")

    print(f"\nHeap blocks: {len(snapshot.heap.blocks)}")
    for addr, block in snapshot.heap.blocks.items():
        print(f"  Block at {hex(addr)}: type={block.type_name}, freed={block.is_freed}")

    print("\n" + "="*70)
    print("Launching GUI...")
    print("="*70)
    print()
    print("INSTRUCTIONS:")
    print("  1. Use the slider or Next button to navigate")
    print("  2. Look for RED ARROWS connecting boxes")
    print("  3. Arrows should go from pointer variables to their targets")
    print()

    # Create visualizer
    visualizer = MemoryVisualizer(snapshots)

    # Add debug callback to check arrow rendering
    original_render = visualizer.renderer._render_pointers

    def debug_render_pointers(snapshot):
        print(f"\n[DEBUG] _render_pointers called for step {snapshot.step_id}")
        print(f"[DEBUG] Item positions tracked: {len(visualizer.renderer.item_positions)}")
        for addr, pos in list(visualizer.renderer.item_positions.items())[:5]:
            print(f"  {hex(addr)}: {pos}")

        # Call original
        original_render(snapshot)

        # Check if arrows were created
        all_items = visualizer.renderer.canvas.find_all()
        arrows = [item for item in all_items if visualizer.renderer.canvas.type(item) == 'line']
        print(f"[DEBUG] Total canvas items: {len(all_items)}")
        print(f"[DEBUG] Arrow items (lines): {len(arrows)}")
        if arrows:
            print(f"[DEBUG] ✓ ARROWS WERE CREATED!")
        else:
            print(f"[DEBUG] ✗ NO ARROWS FOUND!")

    visualizer.renderer._render_pointers = debug_render_pointers

    visualizer.run()


if __name__ == "__main__":
    main()
