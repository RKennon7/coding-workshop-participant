import {createTheme} from '@mui/material/styles';
import '@fontsource-variable/inter';

// basic styling, light and dark themes

// both palettes share the same teal + clay hues so switching modes feels like the
// same app: light mode is cream surfaces with a muted teal, dark mode is a deep
// teal-charcoal with the teal lifted so it stays readable
const palettes = {
    light: {
        primary: { main: '#237A72', light: '#5FB3A9', dark: '#185A54', contrastText: '#FFFFFF' },
        secondary: { main: '#B8714A', light: '#D49A78', dark: '#8A5233', contrastText: '#FFFFFF' },
        background: { default: '#FAF7F0', paper: '#FFFDF8' },
        text: { primary: '#1F2A2E', secondary: '#5B6669' },
        divider: 'rgba(31, 42, 46, 0.12)',
    },
    dark: {
        primary: { main: '#5EC4B6', light: '#8FD8CE', dark: '#3A9488', contrastText: '#0E1A1A' },
        secondary: { main: '#E0A27A', light: '#EBBE9F', dark: '#B97B55', contrastText: '#1A120C' },
        background: { default: '#121A1C', paper: '#1A2427' },
        text: { primary: '#E6EEEC', secondary: '#9FB0AD' },
        divider: 'rgba(230, 238, 236, 0.12)',
    },
};

export function getTheme(mode) {
    return createTheme({
        palette: { mode, ...palettes[mode] },
        shape: { borderRadius: 10 },
        typography: {
            // Inter is designed for UI/data: clear at small sizes, has tabular numbers
            fontFamily: '"Inter Variable", "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
            h1: { fontWeight: 700, letterSpacing: '-0.02em' },
            h2: { fontWeight: 700, letterSpacing: '-0.02em' },
            h3: { fontWeight: 600, letterSpacing: '-0.01em' },
            h4: { fontWeight: 600, letterSpacing: '-0.01em' },
            h5: { fontWeight: 600 },
            h6: { fontWeight: 600 },
            button: { fontWeight: 600, textTransform: 'none' },
        },
        components: {
            MuiCssBaseline: {
                styleOverrides: {
                    // tabular numbers keep columns of figures aligned in tables/stat tiles
                    body: { fontFeatureSettings: '"tnum", "cv11"' },
                },
            },
            // flat header that sits on the page surface instead of a solid color bar
            MuiAppBar: {
                defaultProps: { elevation: 0, color: 'default' },
                styleOverrides: {
                    root: ({theme}) => ({
                        backgroundColor: theme.palette.background.paper,
                        color: theme.palette.text.primary,
                        borderBottom: `1px solid ${theme.palette.divider}`,
                    }),
                },
            },
            MuiPaper: {
                // MUI lightens dark-mode paper with a gradient overlay, which muddies the palette
                styleOverrides: { root: { backgroundImage: 'none' } },
            },
            MuiCard: {
                defaultProps: { variant: 'outlined' },
            },
            MuiButton: {
                defaultProps: { disableElevation: true },
            },
            MuiTextField: {
                defaultProps: { size: 'small' },
            },
            MuiChip: {
                styleOverrides: { root: { fontWeight: 500 } },
            },
            MuiDataGrid: {
                styleOverrides: {
                    root: ({theme}) => ({
                        border: `1px solid ${theme.palette.divider}`,
                        backgroundColor: theme.palette.background.paper,
                        '--DataGrid-containerBackground': theme.palette.background.default,
                    }),
                    columnHeaderTitle: { fontWeight: 600 },
                },
            },
        },
    });
}
