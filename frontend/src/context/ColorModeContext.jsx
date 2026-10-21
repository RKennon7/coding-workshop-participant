import {createContext, useContext, useMemo, useState, useEffect} from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import useMediaQuery from '@mui/material/useMediaQuery';
import { getTheme } from '../theme';

const ColorModeContext = createContext({ mode: 'light', toggleColorMode: () => {} });

export const useColorMode = () => useContext(ColorModeContext);

export function ColorModeProvider({children}) {
    // noSsr reads the real value on the first render so the initial mode below is correct
    const prefersDark = useMediaQuery('(prefers-color-scheme: dark)', { noSsr: true });
    const [mode, setMode] = useState(
        () => localStorage.getItem('colorMode') || (prefersDark ? 'dark' : 'light')
    );

    useEffect(() => {
        localStorage.setItem('colorMode', mode);
    }, [mode]);

    const value = useMemo(
        () => ({
            mode,
            toggleColorMode: () => setMode((m) => (m === 'light' ? 'dark' : 'light')),
        }),
        [mode]
    );

    const theme = useMemo(() => getTheme(mode), [mode]);

    return (
        <ColorModeContext.Provider value={value}>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            {children}
          </ThemeProvider>
        </ColorModeContext.Provider>
    );

}