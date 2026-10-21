import { useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from '@mui/material';
import { getErrorMessage } from '../../hooks/useResource.js';

{/** yes/no dialog for destructive actions. onConfirm can be async, errors are shown in the dialog */}
function ConfirmDialog({open, title, message, confirmLabel = 'Delete', onConfirm, onClose}) {
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
                <DialogContentText>{message}</DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} disabled={busy}>Cancel</Button>
                <Button onClick={handleConfirm} color="error" variant="contained" disabled={busy}>
                    {confirmLabel}
                </Button>
            </DialogActions>
        </Dialog>
    );
}

export default ConfirmDialog;
