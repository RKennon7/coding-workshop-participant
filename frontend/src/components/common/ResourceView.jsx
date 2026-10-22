import { useEffect, useState } from 'react';
import { Alert, Snackbar } from '@mui/material';
import DataTable from './DataTable.jsx';
import EntityFormDialog from './EntityFormDialog.jsx';
import ConfirmDialog from './ConfirmDialog.jsx';
import { usePermissions } from '../../hooks/usePermissions.js';
import { getErrorMessage, useResource } from '../../hooks/useResource.js';

{/**
 * full CRUD screen for one resource: DataTable + add/edit form + delete confirmation
 *  - service: from services/index.js (must be a stable reference, not created during render)
 *  - permissions: {create, update, delete} permission strings for the resource
 *  - fields: EntityFormDialog field definitions. a field can set editableBy: [permissions]
 *    to allow partial edits, e.g. status editable by INCIDENTS_UPDATE or INCIDENTS_UPDATE_STATUS,
 *    or editableBy: (row) => boolean when it depends on the row (e.g. only the ticket's assignee)
 *  - renderFormExtras(row): extra content under the form when editing an existing row (e.g. notes)
 *  - listParams: query params for the list call (e.g. filters), the grid reloads when they change
 *  - filters: content shown between the title and the grid (e.g. a filter bar)
 *  - gridInitialState: passed to the DataGrid's initialState (e.g. hidden columns)
 *  - getDeleteDetails(row): optional async check before deleting -> {message, blocked}. blocked disables the
 *    delete button (e.g. a building that still has incidents), message replaces the default confirmation text
 *  - openRowId / initialCreate: open that row's form (or the create form) on mount, e.g. when the dashboard links here
 * the grid is paged, sorted and searched on the server: only the visible page is loaded
 */}

const DEFAULT_PAGE_SIZE = 25;

// grid sort model -> ?sort=field / ?sort=-field
const toSortParam = (sortModel) => (sortModel[0] ? `${sortModel[0].sort === 'desc' ? '-' : ''}${sortModel[0].field}` : undefined);
function ResourceView({
    title,
    singular,
    service,
    columns,
    fields,
    permissions,
    getRowLabel = (row) => row.name ?? `#${row.id}`,
    renderFormExtras,
    listParams,
    filters,
    gridInitialState,
    getDeleteDetails,
    openRowId = null,
    initialCreate = false,
}) {
    const {can, canAny} = usePermissions();
    // paging/sorting/search. the page goes back to the first one whenever anything else about the list changes
    const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
    const [sortModel, setSortModel] = useState([]);
    const [search, setSearch] = useState('');
    const listKey = JSON.stringify({listParams, pageSize, sortModel, search});
    const [pageState, setPageState] = useState({listKey, page: 0});
    const page = pageState.listKey === listKey ? pageState.page : 0;
    const setPage = (next) => setPageState({listKey, page: next});

    const params = {
        ...listParams,
        limit: pageSize,
        offset: page * pageSize,
        sort: toSortParam(sortModel),
        q: search || undefined,
    };
    const {rows, total, loading, error, create, update, remove} = useResource(service, {params, paged: true});

    // form state: null = closed, otherwise {mode, row}
    const [form, setForm] = useState(() => (initialCreate ? {mode: 'create', row: {}} : null));
    const [deleting, setDeleting] = useState(null);
    // {loading} while getDeleteDetails runs, then {message, blocked}
    const [deleteInfo, setDeleteInfo] = useState(null);

    const startDelete = async (row) => {
        setDeleting(row);
        if (!getDeleteDetails) {
            setDeleteInfo(null);
            return;
        }
        setDeleteInfo({loading: true});
        try {
            setDeleteInfo(await getDeleteDetails(row));
        } catch (err) {
            setDeleteInfo({message: getErrorMessage(err), blocked: true});
        }
    };
    // {message, severity}
    const [toast, setToast] = useState(null);

    // deep link: fetch the row (it may be filtered out of the grid) and open its form
    useEffect(() => {
        if (openRowId == null) {
            return;
        }
        let cancelled = false;
        service.get(openRowId)
            .then((row) => !cancelled && setForm({mode: 'edit', row}))
            .catch((err) => !cancelled && setToast({message: getErrorMessage(err), severity: 'error'}));
        return () => {
            cancelled = true;
        };
    }, [openRowId, service]);

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
            setToast({message: `${singular} created`, severity: 'success'});
            return;
        }
        // PATCH only what changed
        const changes = Object.fromEntries(
            Object.entries(values).filter(([name, value]) => value !== (form.row[name] ?? null))
        );
        if (Object.keys(changes).length > 0) {
            await update(form.row.id, changes);
            setToast({message: `${singular} updated`, severity: 'success'});
        }
    };

    const handleDelete = async () => {
        // deleting the only row on the last page: step back so the grid doesn't show an empty page
        if (rows.length === 1 && page > 0) {
            setPage(page - 1);
        }
        await remove(deleting.id);
        setToast({message: `${singular} deleted`, severity: 'success'});
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
                onDelete={startDelete}
                toolbar={filters}
                initialState={gridInitialState}
                server={{
                    rowCount: total,
                    paginationModel: {page, pageSize},
                    onPaginationModelChange: (model) => {
                        if (model.pageSize !== pageSize) setPageSize(model.pageSize);
                        else setPage(model.page);
                    },
                    sortModel,
                    onSortModelChange: setSortModel,
                    onSearchChange: setSearch,
                }}
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
                message={deleteInfo?.message ?? (deleting ? `"${getRowLabel(deleting)}" will be permanently deleted.` : '')}
                loading={Boolean(deleteInfo?.loading)}
                confirmDisabled={Boolean(deleteInfo?.blocked || deleteInfo?.loading)}
                onConfirm={handleDelete}
                onClose={() => setDeleting(null)}
            />

            <Snackbar
                open={Boolean(toast)}
                autoHideDuration={3000}
                onClose={() => setToast(null)}
                anchorOrigin={{vertical: 'bottom', horizontal: 'center'}}
            >
                <Alert severity={toast?.severity ?? 'success'} variant="filled" onClose={() => setToast(null)}>{toast?.message}</Alert>
            </Snackbar>
        </>
    );
}

export default ResourceView;
