import { useState } from 'react';
import { Alert, Snackbar } from '@mui/material';
import DataTable from './DataTable.jsx';
import EntityFormDialog from './EntityFormDialog.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import { usePermissions } from '../../hooks/usePermissions.js';
import { useResource } from '../../hooks/useResource.js';

{/**
 * full CRUD screen for one resource: DataTable + add/edit form + delete confirmation
 *  - service: from services/index.js (must be a stable reference, not created during render)
 *  - permissions: {create, update, delete} permission strings for the resource
 *  - fields: EntityFormDialog field definitions. a field can set editableBy: [permissions]
 *    to allow partial edits, e.g. status editable by INCIDENTS_UPDATE or INCIDENTS_UPDATE_STATUS,
 *    or editableBy: (row) => boolean when it depends on the row (e.g. only the ticket's assignee)
 *  - renderFormExtras(row): extra content under the form when editing an existing row (e.g. notes)
 */}
function ResourceView({
    title,
    singular,
    service,
    columns,
    fields,
    permissions,
    getRowLabel = (row) => row.name ?? `#${row.id}`,
    renderFormExtras,
}) {
    const {can, canAny} = usePermissions();
    const {rows, loading, error, create, update, remove} = useResource(service);

    // form state: null = closed, otherwise {mode, row}
    const [form, setForm] = useState(null);
    const [deleting, setDeleting] = useState(null);
    const [toast, setToast] = useState(null);

    const canCreate = can(permissions.create);
    const canDelete = can(permissions.delete);
    const isRowRule = (field) => typeof field.editableBy === 'function';
    const isEditable = (field, row) => (isRowRule(field) ? field.editableBy(row) : canAny(field.editableBy ?? [permissions.update]));
    // show the edit action if the user can change at least one field. row-dependent fields count,
    // the form then disables whatever this particular row doesn't allow (read-only if nothing)
    const canEdit = fields.some((field) => !field.createOnly && (isRowRule(field) || isEditable(field)));

    const openCreate = () => setForm({mode: 'create', row: {}});
    const openEdit = (row) => setForm({mode: 'edit', row});

    const handleSubmit = async (values) => {
        if (form.mode === 'create') {
            await create(values);
            setToast(`${singular} created`);
            return;
        }
        // PATCH only what changed
        const changes = Object.fromEntries(
            Object.entries(values).filter(([name, value]) => value !== (form.row[name] ?? null))
        );
        if (Object.keys(changes).length > 0) {
            await update(form.row.id, changes);
            setToast(`${singular} updated`);
        }
    };

    const handleDelete = async () => {
        await remove(deleting.id);
        setToast(`${singular} deleted`);
    };

    return (
        <>
            <DataTable
                title={title}
                rows={rows}
                columns={columns}
                loading={loading}
                error={error}
                addLabel={`Add ${singular}`}
                canAdd={canCreate}
                canEdit={canEdit}
                canDelete={canDelete}
                onAdd={openCreate}
                onEdit={openEdit}
                onDelete={setDeleting}
            />

            {form && (
                <EntityFormDialog
                    // remount for each row so the form starts from that row's values
                    key={form.mode === 'create' ? 'new' : form.row.id}
                    open
                    mode={form.mode}
                    title={form.mode === 'create' ? `New ${singular}` : getRowLabel(form.row)}
                    fields={fields}
                    initialValues={form.row}
                    isFieldEditable={(field) => (form.mode === 'create' ? canCreate : isEditable(field, form.row))}
                    onSubmit={handleSubmit}
                    onClose={() => setForm(null)}
                >
                    {form.mode === 'edit' && renderFormExtras?.(form.row)}
                </EntityFormDialog>
            )}

            <ConfirmDialog
                open={Boolean(deleting)}
                title={`Delete ${singular.toLowerCase()}?`}
                message={deleting ? `"${getRowLabel(deleting)}" will be permanently deleted.` : ''}
                onConfirm={handleDelete}
                onClose={() => setDeleting(null)}
            />

            <Snackbar
                open={Boolean(toast)}
                autoHideDuration={3000}
                onClose={() => setToast(null)}
                anchorOrigin={{vertical: 'bottom', horizontal: 'center'}}
            >
                <Alert severity="success" variant="filled" onClose={() => setToast(null)}>{toast}</Alert>
            </Snackbar>
        </>
    );
}

export default ResourceView;
