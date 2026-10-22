// in-app navigation between the main tabs. the app has no URL router (no react-router):
// the active tab lives in MainLayout's state, and this context is how pages change it
import { createContext, useContext } from 'react';

/**
 * Lets any page switch the main tab and hand the next page some params, e.g. the dashboard
 * opening the Incidents tab already filtered: navigate('incidents', {filters: {status: ['Blocked']}})
 * MainLayout provides the value; the active page receives the params as a `params` prop.
 * Tab ids are the `id`s in components/layout/navigation.js. Every navigate() remounts the
 * target page, so it re-reads its params even if it was already the active tab.
 */

export const NavigationContext = createContext(null);

/**
 * @returns {{navigate: (id: string, params?: object | null) => void}}
 * @throws if used outside MainLayout (e.g. on the login screen)
 */
export function useNavigation() {
    const context = useContext(NavigationContext);
    if (context === null) {
        throw new Error('useNavigation must be used within MainLayout');
    }
    return context;
}
