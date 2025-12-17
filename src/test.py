import flet as ft
from backend import Backend
from turkey_manager import TurkeyManager

def main(page: ft.Page):
    backend = Backend()

    # ListViews
    turkey_lv = ft.ListView(expand=True, spacing=5, padding=10)
    order_lv = ft.ListView(expand=True, spacing=5, padding=10)

    # --- Manager ---
    # Define turkey_manager first
    turkey_manager = TurkeyManager(backend, None)  # temporarily None

    # --- Refresh function ---
    def refresh_ui():
        # Update turkeys
        turkey_lv.controls.clear()
        for tid, t in turkey_manager.get_sorted_turkeys().to_dict("index").items():
            turkey_lv.controls.append(
                ft.ListTile(
                    title=ft.Text(f"TID: {tid}, Weight: {t['weight']}, Assigned: {t['assigned']}"),
                    selected=(tid == turkey_manager.selected_turkey),
                    on_click=lambda e, tid=tid: turkey_manager.select_turkey(tid)
                )
            )

        # Update orders
        order_lv.controls.clear()
        for oid, o in turkey_manager.get_sorted_orders().to_dict("index").items():
            order_lv.controls.append(
                ft.ListTile(
                    title=ft.Text(f"OID: {oid}, Name: {o['name']}, Target: {o['target_weight']}, Assigned: {o['assigned_weight']}"),
                    subtitle=ft.Text(f"Notes: {o['notes']}"),
                    selected=(oid == turkey_manager.selected_order),
                    on_click=lambda e, oid=oid: turkey_manager.select_order(oid)
                )
            )

        turkey_lv.update()
        order_lv.update()

    # Set the refresh function in the manager
    turkey_manager.set_refresh_callback(refresh_ui)

    # --- Buttons ---
    add_turkey_btn = ft.ElevatedButton("Add Turkey", on_click=lambda e: turkey_manager.add_turkey(1, 15))
    delete_turkey_btn = ft.ElevatedButton("Delete Selected Turkey", on_click=lambda e: turkey_manager.delete_selected_turkey())
    auto_match_btn = ft.ElevatedButton("Auto Match", on_click=lambda e: turkey_manager.auto_match())

    # --- Add ListViews to page first ---
    page.add(
        ft.Column([
            turkey_lv,
            order_lv,
            add_turkey_btn,
            delete_turkey_btn,
            auto_match_btn,
        ])
    )

    # --- Safe to call refresh ---
    refresh_ui()

