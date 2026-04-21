# JS Components
*Location: `src/static/js/dashboard/components/`*

**Responsibility**: Reusable UI widgets, interactive modals, and shared DOM utility functions.

---

## Modals

### openEditModal(config, actionTarget)
*Location: `src/static/js/dashboard/components/edit_modal.js`*
Displays the modal with custom fields and callbacks.

### closeEditModal()
*Location: `src/static/js/dashboard/components/edit_modal.js`*
Hides the edit modal.

### openLinkModal(config)
*Location: `src/static/js/dashboard/components/link_modal.js`*
Displays the searchable link selector.

### closeLinkModal()
*Location: `src/static/js/dashboard/components/link_modal.js`*
Hides the link modal.

### showConfirm(message, options)
*Location: `src/static/js/dashboard/components/confirm_modal.js`*
Returns a Promise resolving to `true` on OK.

### openScrubberModal(songId, title, options)
*Location: `src/static/js/dashboard/components/scrubber_modal.js`*
Initializes playback and waveform for a song.

### closeScrubberModal()
*Location: `src/static/js/dashboard/components/scrubber_modal.js`*
Stops playback and hides modal.

### openSpotifyModal(songId, title)
*Location: `src/static/js/dashboard/components/spotify_modal.js`*
Displays the credit importer.

### closeSpotifyModal()
*Location: `src/static/js/dashboard/components/spotify_modal.js`*
Hides the spotify modal.

### openSplitterModal(config)
*Location: `src/static/js/dashboard/components/splitter_modal.js`*
Displays the name/credit splitting tool.

### closeSplitterModal()
*Location: `src/static/js/dashboard/components/splitter_modal.js`*
Hides the splitter modal.

### openFilenameParserModal(config)
*Location: `src/static/js/dashboard/components/filename_parser_modal.js`*
Displays the regex-based extractor.

### closeFilenameParserModal()
*Location: `src/static/js/dashboard/components/filename_parser_modal.js`*
Hides the filename parser modal.

---

## Widgets

### activateInlineEdit(target, config)
*Location: `src/static/js/dashboard/components/inline_editor.js`*
Replaces a text span with an input field and handles commit/revert.

### createChipInput(container, chips, options)
*Location: `src/static/js/dashboard/components/chip_input.js`*
Renders a collection of removable chips with an add-input.

### initToastSystem()
*Location: `src/static/js/dashboard/components/toast.js`*
Bootstraps the toast container.

### showToast(msg, type)
*Location: `src/static/js/dashboard/components/toast.js`*
Displays a temporary banner (info, success, error).

---

## Shared Utilities
*Location: `src/static/js/dashboard/components/utils.js`*

### renderSongList(songs, emptyMessage)
Renders a vertical list of song rows with standardized metadata layout.

### renderAuditTimeline(history)
Renders a vertical chronological list of audit entries.

### renderEmptyState(container, message)
Renders a centered placeholder view.

### renderModuleToolbar(container, actions)
Renders a standardized toolbar with action buttons.

### isModalOpen()
Returns true if any major modal is currently visible.

### escapeHtml(str)
Standard HTML escaping utility.

### pluralize(count, singular, plural)
Returns formatted string based on count.

### basename(path)
Extracts the filename from a full path.

### asArray(val)
Ensures a value is treated as an array.

### buildNavigateAttrs(mode, query)
Utility to build `data-action="navigate-search"` attributes.

### formatCountLabel(count, label)
Formats a label with an optional parenthesized count.

### renderStatus(status)
Returns HTML for a processing status badge.

### textOrDash(val)
Returns value or a horizontal dash if empty.

### wasMousedownInside(event, element)
Helper for click-outside detection.
