import flet as ft
from backend import Backend

class TurkeyManager:
    def __init__(self, backend: Backend, turkey_lv: ft.ListView):
        self.backend = backend
        self.turkey_lv = turkey_lv

        # Sorting
        self.sort_modes = [
            "tid_asc",
            "tid_desc",
            "weight_asc",
            "weight_desc",
            "unassigned_weight_asc",
            "unassigned_weight_desc"
        ]
        self.sort_index = 0
        self.current_sort = self.sort_modes[self.sort_index]

        # Selected turkey
        self.selected_turkey = None

        # Sort button
        self.sort_button = ft.ElevatedButton(
            text=f"Turkey Sort: {self.current_sort}",
            on_click=self.cycle_sort
        )

    def refresh_turkeys(self):
        self.turkey_lv.controls.clear()

        # Sorting options
        sort_options = {
            "tid_asc": lambda df: df.sort_values("tid", ascending=True),
            "tid_desc": lambda df: df.sort_values("tid", ascending=False),
            "weight_asc": lambda df: df.sort_values("weight", ascending=True),
            "weight_desc": lambda df: df.sort_values("weight", ascending=False),
            "unassigned_weight_asc": lambda df: df[df["assigned"] == False].sort_values("weight", ascending=True),
            "unassigned_weight_desc": lambda df: df[df["assigned"] == False].sort_values("weight", ascending=False),
        }

        sorted_turkeys = sort_options[self.current_sort](self.backend.turkeys)

        # Populate ListView
        for tid, turkey in sorted_turkeys.to_dict("index").items():
            self.turkey_lv.controls.append(
                ft.ListTile(
                    title=ft.Text(f"TID: {tid}, Weight: {turkey['weight']}, Assigned: {turkey['assigned']}"),
                    data=tid,
                    selected=(tid == self.selected_turkey),
                    on_click=lambda e, tid=tid: self.select_turkey(tid)
                )
            )
        self.turkey_lv.update()

    def select_turkey(self, tid):
        self.selected_turkey = tid
        self.refresh_turkeys()

    def cycle_sort(self, e=None):
        self.sort_index = (self.sort_index + 1) % len(self.sort_modes)
        self.current_sort = self.sort_modes[self.sort_index]
        self.sort_button.text = f"Turkey Sort: {self.current_sort}"
        self.sort_button.update()
        self.refresh_turkeys()

    def add_turkey(self, tid, weight):
        self.backend.add_turkey(tid, weight)
        self.refresh_turkeys()

    def delete_selected(self):
        if self.selected_turkey is not None:
            self.backend.remove_turkey(self.selected_turkey)
            self.selected_turkey = None
            self.refresh_turkeys()

    def unmatch_selected(self):
        if self.selected_turkey is not None:
            self.backend.remove_match_by_tid(self.selected_turkey)
            self.refresh_turkeys()

def main(page: ft.Page):
    backend = Backend()

    # Turkey inputs
    tid_input = ft.TextField(label="Turkey ID", width=100)
    weight_input = ft.TextField(label="Weight", width=100)
    turkey_lv = ft.ListView(expand=True, spacing=5, padding=10)

    # Create the manager
    turkey_manager = TurkeyManager(backend, turkey_lv)

    # Buttons use the manager methods
    add_turkey_button = ft.ElevatedButton(
        "Add Turkey",
        on_click=lambda e: turkey_manager.add_turkey(
            int(tid_input.value), float(weight_input.value)
        )
    )
    delete_button = ft.ElevatedButton(
        "Delete Selected Turkey",
        on_click=lambda e: turkey_manager.delete_selected()
    )
    unmatch_button = ft.ElevatedButton(
        "Unmatch Selected Turkey",
        on_click=lambda e: turkey_manager.unmatch_selected()
    )

    # Layout
    page.add(
        ft.Column([
            ft.Row([tid_input, weight_input, add_turkey_button]),
            turkey_lv,
            delete_button,
            unmatch_button,
            turkey_manager.sort_button  # sort button integrated
        ])
    )

    # Add test turkeys
    for tid, weight in [(1,18),(2,15),(3,17),(4,13),(5,19)]:
        turkey_manager.add_turkey(tid, weight)
