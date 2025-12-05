# frames/library/context_actions.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

"""
Acts as a facade for context menu actions, re-exporting functions from
the 'actions' subpackage to maintain compatibility with existing modules.
"""

from .actions import book_actions
from .actions import shelf_actions
from .actions import metadata_actions
from .actions import action_utils

# Re-export Helper Functions
# We map the new public names to the old private names if needed for compatibility,
# or just expose them directly if we updated the callers.
# Since we updated callers to use action_utils directly in many places, this might be redundant,
# but kept for any external references.

get_map_index = action_utils.get_map_index
get_focused_book_info = action_utils.get_focused_book_info
get_focused_shelf_info = action_utils.get_focused_shelf_info
get_selected_book_data_list = action_utils.get_selected_book_data_list
get_selected_shelf_data_list = action_utils.get_selected_shelf_data_list
refresh_all_views = action_utils.refresh_all_views

# Map old private names for backward compatibility (if any module still uses them)
_get_map_index = action_utils.get_map_index
_get_focused_book_info = action_utils.get_focused_book_info
_get_focused_shelf_info = action_utils.get_focused_shelf_info
_get_selected_book_data_list = action_utils.get_selected_book_data_list
_get_selected_shelf_data_list = action_utils.get_selected_shelf_data_list
_refresh_all_views = action_utils.refresh_all_views

# Re-export Book Actions
on_context_play = book_actions.on_context_play
on_context_rename_book = book_actions.on_context_rename_book
on_context_properties = book_actions.on_context_properties
on_context_open_location = book_actions.on_context_open_location
on_context_update_location = book_actions.on_context_update_location
on_context_delete_book = book_actions.on_context_delete_book
on_context_delete_computer = book_actions.on_context_delete_computer
on_context_pin_book = book_actions.on_context_pin_book
on_context_unpin_book = book_actions.on_context_unpin_book
on_context_mark_finished = book_actions.on_context_mark_finished
on_context_mark_unfinished = book_actions.on_context_mark_unfinished

# Re-export Shelf Actions
on_context_move_to_shelf = shelf_actions.on_context_move_to_shelf
on_context_move_to_new_shelf = shelf_actions.on_context_move_to_new_shelf
on_context_rename_shelf = shelf_actions.on_context_rename_shelf
on_context_delete_shelf = shelf_actions.on_context_delete_shelf

# Re-export Metadata Actions
on_context_export_data = metadata_actions.on_context_export_data
