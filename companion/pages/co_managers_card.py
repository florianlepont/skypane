"""Shared contracts for frame co-management: the three POST route paths, the
form field names, the flash keys and their texts. The co-managers card markup
for the frame's Home page is added to this module later, so the handlers, the
card and the flash registry all read one definition.

Pure: no I/O, no request state.
"""
from companion import i18n

ADD_ROUTE = "/co-managers/add"
REMOVE_ROUTE = "/co-managers/remove"
LEAVE_ROUTE = "/co-managers/leave"

FIELD_EMAIL = "email"
FIELD_USER_ID = "user_id"

FLASH_ADDED = "co_manager_added"
FLASH_REMOVED = "co_manager_removed"
FLASH_LEFT = "co_manager_left"
FLASH_ADD_REFUSED = "co_manager_add_refused"
FLASH_FAILED = "co_manager_failed"
FLASH_LEAVE_NOOP = "co_manager_leave_noop"

# None of these texts carries a placeholder: the typed address, an id or a
# frame name never reaches a flash.
FLASH_ADDED_TEXT = i18n.msg(
    "co_managers.flash_added",
    "Co-manager added — they can now manage this frame.")
FLASH_REMOVED_TEXT = i18n.msg(
    "co_managers.flash_removed",
    "Co-manager removed — they no longer have access to this frame.")
FLASH_LEFT_TEXT = i18n.msg(
    "co_managers.flash_left",
    "You left the frame — it no longer appears in your account.")
FLASH_ADD_REFUSED_TEXT = i18n.msg(
    "co_managers.flash_add_refused",
    "That address can't be added — check the spelling, or ask an "
    "administrator to invite this person first.")
FLASH_FAILED_TEXT = i18n.msg(
    "co_managers.flash_failed",
    "Couldn't update co-managers — try again in a moment.")
FLASH_LEAVE_NOOP_TEXT = i18n.msg(
    "co_managers.flash_leave_noop",
    "Nothing changed — only co-managers can leave a frame.")
