import flet as ft
import pandas as pd
from backend import Backend
from turkey_manager import TurkeyManager

def main(page: ft.Page):
    backend = Backend()
    turkey_manager = TurkeyManager(backend, lambda: refresh_ui())

    # --- Sort state ---
    turkey_sort_col = "tid"
    turkey_sort_asc = True
    order_sort_col = "oid"
    order_sort_asc = True

    # --- Header arrows helper ---
    def arrow(col, current_col, asc):
        if col == current_col:
            return "↑" if asc else "↓"
        return ""

    # --- DataTables ---
    turkey_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(f"TID {arrow('tid', turkey_sort_col, turkey_sort_asc)}"), on_sort=lambda e: sort_turkeys("tid")),
            ft.DataColumn(ft.Text(f"Weight {arrow('weight', turkey_sort_col, turkey_sort_asc)}"), on_sort=lambda e: sort_turkeys("weight")),
            ft.DataColumn(ft.Text("Assigned")),
        ],
        rows=[]
    )

    order_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(f"OID {arrow('oid', order_sort_col, order_sort_asc)}"), on_sort=lambda e: sort_orders("oid")),
            ft.DataColumn(ft.Text(f"Name {arrow('name', order_sort_col, order_sort_asc)}"), on_sort=lambda e: sort_orders("name")),
            ft.DataColumn(ft.Text(f"Target {arrow('target_weight', order_sort_col, order_sort_asc)}"), on_sort=lambda e: sort_orders("target_weight")),
            ft.DataColumn(ft.Text("Ham")),
            ft.DataColumn(ft.Text("Matched")),
            ft.DataColumn(ft.Text("Weight")),
            ft.DataColumn(ft.Text("Notes")),
        ],
        rows=[]
    )

    # --- Sort functions ---
    def sort_turkeys(col):
        nonlocal turkey_sort_col, turkey_sort_asc
        if turkey_sort_col == col:
            turkey_sort_asc = not turkey_sort_asc
        else:
            turkey_sort_col = col
            turkey_sort_asc = True
        refresh_ui()

    def sort_orders(col):
        nonlocal order_sort_col, order_sort_asc
        if order_sort_col == col:
            order_sort_asc = not order_sort_asc
        else:
            order_sort_col = col
            order_sort_asc = True
        refresh_ui()

    # --- Refresh function ---
    def refresh_ui():
        nonlocal turkey_table, order_table

        # --- Update turkey table ---
        df_turkeys = turkey_manager.get_sorted_turkeys().sort_values(
            turkey_sort_col, ascending=turkey_sort_asc
        )
        turkey_table.rows.clear()
        for tid, t in df_turkeys.to_dict("index").items():
            assigned_text = "Yes" if t["assigned"] else "No"
            assigned_color = ft.Colors.GREEN if t["assigned"] else ft.Colors.RED
            turkey_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(tid))),
                        ft.DataCell(ft.Text(str(t["weight"]))),
                        ft.DataCell(ft.Text(assigned_text, color=assigned_color)),
                    ],
                    selected=(tid == turkey_manager.selected_turkey),
                    on_select_changed=lambda e, tid=tid: turkey_manager.select_turkey(tid),
                )
            )

        # Rebuild columns with updated arrows
        turkey_table.columns = [
            ft.DataColumn(
                ft.Text(f"TID {arrow('tid', turkey_sort_col, turkey_sort_asc)}"),
                on_sort=lambda e: sort_turkeys("tid")
            ),
            ft.DataColumn(
                ft.Text(f"Weight {arrow('weight', turkey_sort_col, turkey_sort_asc)}"),
                on_sort=lambda e: sort_turkeys("weight")
            ),
            ft.DataColumn(ft.Text("Assigned")),
        ]
        turkey_table.update()

        # --- Update order table ---
        df_orders = turkey_manager.get_sorted_orders().sort_values(
            order_sort_col, ascending=order_sort_asc
        )
        order_table.rows.clear()
        for oid, o in df_orders.to_dict("index").items():
            assigned_tid = str(o["assigned_tid"]) if pd.notna(o["assigned_tid"]) else "No"
            assigned_tid_color = ft.Colors.GREEN if pd.notna(o["assigned_tid"]) else ft.Colors.RED

            assigned_weight = str(o["assigned_weight"]) if pd.notna(o["assigned_weight"]) else "No"
            assigned_weight_color = ft.Colors.GREEN if pd.notna(o["assigned_weight"]) else ft.Colors.RED

            order_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(oid))),
                        ft.DataCell(ft.Text(o["name"])),
                        ft.DataCell(ft.Text(str(o["target_weight"]))),
                        ft.DataCell(ft.Text(o["ham"])),
                        ft.DataCell(ft.Text(assigned_tid, color=assigned_tid_color)),
                        ft.DataCell(ft.Text(assigned_weight, color=assigned_weight_color)),
                        ft.DataCell(ft.Text(o["notes"])),
                    ],
                    selected=(oid == turkey_manager.selected_order),
                    on_select_changed=lambda e, oid=oid: turkey_manager.select_order(oid),
                )
            )

        # Rebuild order table headers with arrows
        order_table.columns = [
            ft.DataColumn(
                ft.Text(f"OID {arrow('oid', order_sort_col, order_sort_asc)}"),
                on_sort=lambda e: sort_orders("oid")
            ),
            ft.DataColumn(
                ft.Text(f"Name {arrow('name', order_sort_col, order_sort_asc)}"),
                on_sort=lambda e: sort_orders("name")
            ),
            ft.DataColumn(
                ft.Text(f"Target {arrow('target_weight', order_sort_col, order_sort_asc)}"),
                on_sort=lambda e: sort_orders("target_weight")
            ),
            ft.DataColumn(ft.Text("Ham")),
            ft.DataColumn(ft.Text("Matched")),
            ft.DataColumn(ft.Text("Weight")),
            ft.DataColumn(ft.Text("Notes")),
        ]
        order_table.update()

    # --- Layout ---
    page.add(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Row([turkey_manager.tid_input, turkey_manager.weight_input], spacing=10,alignment=ft.MainAxisAlignment.CENTER,),
                        ft.Row([turkey_manager.add_turkey_btn, turkey_manager.delete_turkey_btn], spacing=10,alignment=ft.MainAxisAlignment.CENTER,),
                        ft.Container(
                            content=ft.Column([turkey_table], expand=True, scroll=ft.ScrollMode.AUTO),
                            expand=True,
                            padding=5,
                        ),
                    ],
                    expand=False,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        turkey_manager.auto_match_btn,
                        turkey_manager.match_btn,
                        turkey_manager.unmatch_turkey_btn,
                        turkey_manager.unmatch_order_btn,
                        turkey_manager.make_pdfs_btn,
                    ],
                    expand=False,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Row([turkey_manager.oid_input, turkey_manager.order_name_input,turkey_manager.target_weight_input], spacing=10,alignment=ft.MainAxisAlignment.CENTER,),
                        ft.Row([turkey_manager.notes_input, turkey_manager.ham_radio_group], spacing=10,alignment=ft.MainAxisAlignment.CENTER,),
                        ft.Row([turkey_manager.add_order_btn, turkey_manager.delete_order_btn], spacing=10,alignment=ft.MainAxisAlignment.CENTER,),
                        ft.Container(
                            content=ft.Column([order_table], expand=True, scroll=ft.ScrollMode.AUTO),
                            expand=True,
                            padding=5,
                        ),
                    ],
                    expand=True,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            expand=True,
            spacing=20,
        ),
    )

    refresh_ui()

ft.app(target=main)











