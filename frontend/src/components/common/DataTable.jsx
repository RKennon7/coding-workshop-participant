import { useMemo } from 'react';
import { Alert, Box, Button, Stack, Typography } from '@mui/material';
import { DataGrid, GridActionsCellItem } from '@mui/x-data-grid';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

{/**
 * reusable grid for any backend model
 *  - columns: normal MUI X column definitions, an actions column (edit/delete) is appended for you
 *  - canAdd/canEdit/canDelete: hide the matching button when the user isn't allowed to use it
 *  - onRowClick: clicking anywhere on a row except the action buttons (defaults to onEdit)
 *  - includes the grid toolbar with quick search + filters
 *  - toolbar: extra content between the title and the grid (e.g. server-side filters)
 */}
function DataTable({
    title,
    rows,
    columns,
    loading = false,
    error = null,
    addLabel = 'Add',
    canAdd = false,
    canEdit = false,
    canDelete = false,
    onAdd,
    onEdit,
    onDelete,
    onRowClick = onEdit,
    getRowId,
    initialState,
    height = 560,
    toolbar,
}) {
    const gridColumns = useMemo(() => {
        if (!canEdit && !canDelete) {
            return columns;
        }
        const actionsColumn = {
            field: 'actions',
            type: 'actions',
            headerName: 'Actions',
            width: 100,
            getActions: (params) => [
                ...(canEdit ? [
                    <GridActionsCellItem key="edit" icon={<EditIcon />} label="Edit" onClick={() => onEdit(params.row)} />,
                ] : []),
                ...(canDelete ? [
                    <GridActionsCellItem key="delete" icon={<DeleteIcon />} label="Delete" onClick={() => onDelete(params.row)} />,
                ] : []),
            ],
        };
        return [...columns, actionsColumn];
    }, [columns, canEdit, canDelete, onEdit, onDelete]);

    // use cell clicks instead of onRowClick so pressing edit/delete doesn't also open the form
    const handleCellClick = (params) => {
        if (params.field !== 'actions' && onRowClick) {
            onRowClick(params.row);
        }
    };

    return (
        <Stack spacing={2}>
            <Stack direction="row" sx={{alignItems: 'center', justifyContent: 'space-between', gap: 2}}>
                <Typography variant="h6" component="h2">{title}</Typography>
                {canAdd && (
                    <Button variant="contained" startIcon={<AddIcon />} onClick={onAdd}>
                        {addLabel}
                    </Button>
                )}
            </Stack>
            {toolbar}
            {error && <Alert severity="error">{error}</Alert>}
            <Box sx={{height, width: '100%'}}>
                <DataGrid
                    rows={rows}
                    columns={gridColumns}
                    loading={loading}
                    getRowId={getRowId}
                    onCellClick={handleCellClick}
                    initialState={{
                        pagination: {paginationModel: {pageSize: 25}},
                        ...initialState,
                    }}
                    pageSizeOptions={[10, 25, 50, 100]}
                    showToolbar
                    disableRowSelectionOnClick
                    sx={{'& .MuiDataGrid-row': {cursor: onRowClick ? 'pointer' : 'default'}}}
                />
            </Box>
        </Stack>
    );
}

export default DataTable;
