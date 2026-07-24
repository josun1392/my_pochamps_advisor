# v14.22 Advice Window Teardown

`MainWindow.closeEvent` now sets a permanent closing flag and invalidates the
active advice owner/token/terminal claim. Current callback checks include the
flag, so late success and failure cannot update UI. Finished callbacks still
perform one-time cleanup of their own thread object but cannot change active
lifecycle state. Starts after close return before worker/thread creation.

This is not cancellation: workers finish naturally. Real OS teardown races and
non-terminating workers remain gaps. Provider budget is zero.
