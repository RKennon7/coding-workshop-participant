// generic "are you sure?" dialog for destructive actions.
// used by ResourceView for every row delete (incidents, facilities, engineers, users), so any role
// that has a delete permission sees it. on its own it doesn't check permissions: the caller decides
// when to open it, and the backend still enforces who may delete what.
import { useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, LinearProgress } from '@mui/material';
import { getErrorMessage } from '../../hooks/useResource.js';

{/**
 * Yes/no dialog for destructive actions.
 *  - open / onClose: controlled by the parent. onClose runs on Cancel and after a successful confirm
 *  - title, message: message may be text or elements
 *  - confirmLabel: text of the red button (default 'Delete')
 *  - onConfirm: may be async. while it runs both buttons are disabled. if it throws, the dialog stays
 *    open and shows the API error (via getErrorMessage) so the user can retry or cancel
 *  - loading: shows a progress bar instead of the message (e.g. while checking what would be deleted)
 *  - confirmDisabled: greys out the confirm button (e.g. the delete isn't allowed)
 */}
function ConfirmDialog({open, title, message, confirmLabel = 'Delete', onConfirm, onClose, loading = false, confirmDisabled = false}) {
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);

    const handleConfirm = async () => {
        setBusy(true);
        setError(null);
        try {
            await onConfirm();
            onClose();
        } catch (err) {
            setError(getErrorMessage(err));
        } finally {
            setBusy(false);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
            <DialogTitle>{title}</DialogTitle>
            <DialogContent>
                {error && <Alert severity="error" sx={{mb: 2}}>{error}</Alert>}
                {loading ? <LinearProgress /> : <DialogContentText component="div">{message}</DialogContentText>}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} disabled={busy}>Cancel</Button>
                <Button onClick={handleConfirm} color="error" variant="contained" disabled={busy || confirmDisabled}>
                    {confirmLabel}
                </Button>
            </DialogActions>
        </Dialog>
    );
}

export default ConfirmDialog;
