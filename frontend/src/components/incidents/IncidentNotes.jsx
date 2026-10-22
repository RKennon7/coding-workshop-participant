import { useMemo, useState } from 'react';
import {
    Alert, Box, Button, Checkbox, Chip, Divider, FormControlLabel, IconButton, Stack, TextField, Tooltip, Typography,
} from '@mui/material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlined';
import { incidentNotesService } from '../../services/index.js';
import { useAuth } from '../../context/AuthContext.jsx';
import { getErrorMessage, useResource } from '../../hooks/useResource.js';
import { usePermissions } from '../../hooks/usePermissions.js';
import { PERMISSIONS } from '../../auth/permissions.js';
import { formatDateTime } from '../../utils/format.js';
import Can from '../auth/Can.jsx';

{/** notes thread shown inside the incident form: list + add note. closed tickets only take notes from admins */}
function IncidentNotes({incidentId, closed = false}) {
    const {user} = useAuth();
    const {can} = usePermissions();
    const canSeeInternal = can(PERMISSIONS.INCIDENT_NOTES_INTERNAL);
    // INCIDENTS_UPDATE = admin: may add notes to closed tickets and delete anyone's notes
    const isAdmin = can(PERMISSIONS.INCIDENTS_UPDATE);
    const canAdd = !closed || isAdmin;

    // memoized so useResource doesn't refetch on every render
    const service = useMemo(() => incidentNotesService(incidentId), [incidentId]);
    const {rows, loading, error, create, remove} = useResource(service);

    const [body, setBody] = useState('');
    const [isInternal, setIsInternal] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saveError, setSaveError] = useState(null);

    const handleDelete = async (noteId) => {
        setSaveError(null);
        try {
            await remove(noteId);
        } catch (err) {
            setSaveError(getErrorMessage(err));
        }
    };

    // backend should already filter these out for employees, this is a second safety net
    const notes = canSeeInternal ? rows : rows.filter((note) => !note.is_internal);

    // the note form sits inside the incident <form>, so it can't be a nested <form> itself
    const handleAdd = async () => {
        setSaving(true);
        setSaveError(null);
        try {
            await create({body: body.trim(), is_internal: isInternal});
            setBody('');
            setIsInternal(false);
        } catch (err) {
            setSaveError(getErrorMessage(err));
        } finally {
            setSaving(false);
        }
    };

    return (
        <Box>
            <Divider sx={{mb: 2}} />
            <Typography variant="subtitle1" gutterBottom>Notes</Typography>
            {error && <Alert severity="error" sx={{mb: 1}}>{error}</Alert>}
            <Stack spacing={1.5} sx={{mb: 2}}>
                {!loading && notes.length === 0 && (
                    <Typography variant="body2" color="text.secondary">No notes yet.</Typography>
                )}
                {notes.map((note) => (
                    <Box key={note.id} sx={{p: 1.5, borderRadius: 1, bgcolor: 'action.hover'}}>
                        <Stack direction="row" spacing={1} sx={{alignItems: 'center', mb: 0.5}}>
                            <Typography variant="body2" fontWeight={600}>
                                {note.author?.username ?? `User #${note.author_id}`}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                                {formatDateTime(note.created_at)}
                            </Typography>
                            {note.is_internal && <Chip label="Internal" size="small" color="warning" variant="outlined" />}
                            {(note.author_id === user?.uid || isAdmin) && (
                                <Tooltip title="Delete note">
                                    <IconButton size="small" onClick={() => handleDelete(note.id)} sx={{ml: 'auto'}} aria-label="Delete note">
                                        <DeleteOutlineIcon fontSize="small" />
                                    </IconButton>
                                </Tooltip>
                            )}
                        </Stack>
                        <Typography variant="body2" sx={{whiteSpace: 'pre-wrap'}}>{note.body}</Typography>
                    </Box>
                ))}
            </Stack>

            {saveError && <Alert severity="error" sx={{mb: 1}}>{saveError}</Alert>}
            {!canAdd && (
                <Typography variant="body2" color="text.secondary">
                    This incident is closed, so no more notes can be added.
                </Typography>
            )}
            {canAdd && <Can permission={PERMISSIONS.INCIDENT_NOTES_CREATE}>
                <Stack spacing={1}>
                    <TextField
                        label="Add a note"
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                        multiline
                        minRows={2}
                        fullWidth
                        disabled={saving}
                    />
                    <Stack direction="row" sx={{justifyContent: 'space-between', alignItems: 'center'}}>
                        {canSeeInternal ? (
                            <FormControlLabel
                                label="Internal (hidden from employees)"
                                control={<Checkbox checked={isInternal} onChange={(e) => setIsInternal(e.target.checked)} />}
                            />
                        ) : <span />}
                        <Button variant="outlined" onClick={handleAdd} disabled={saving || !body.trim()}>
                            Add Note
                        </Button>
                    </Stack>
                </Stack>
            </Can>}
        </Box>
    );
}

export default IncidentNotes;
