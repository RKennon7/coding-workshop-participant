/**
 * Login state for the whole app. AuthProvider (mounted in App.jsx) owns the JWT access token,
 * keeps it in localStorage under 'accessToken' (api/client.js reads it from there for every request)
 * and decodes it into `user`. Components read it with useAuth(); permission checks go through
 * hooks/usePermissions.js, which uses user.role.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import apiClient, { setUnauthorizedHandler } from "../api/client";
import { registerAccount } from "../services/index.js";

/**
 * Global auth state using React's context API
 */

const AuthContext = createContext(null);

// extract + decode user payload from JWT, returns null if the token is malformed.
// this only reads the claims for display/UI gating, it doesn't verify the signature: the backend does that
function decodeToken(token){
    try {
        // JWTs are base64url encoded, convert to regular base64 before decoding
        const payloadSegment = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(payloadSegment));
        // note: atob means ASCII to Binary
    } catch {
        return null;
    }
}

// exp claim is in seconds since epoch, Date.now() is in ms.
// an undecodable token counts as expired; a token without exp never expires here
function isExpired(payload){
    return !payload || (payload.exp && payload.exp * 1000 <= Date.now());
}

// read the stored token on startup, discarding it if it has already expired
function loadStoredToken(){
    const stored = localStorage.getItem('accessToken');
    if (stored && isExpired(decodeToken(stored))) {
        localStorage.removeItem('accessToken');
        return null;
    }
    return stored;
}

/**
 * AuthProvider wraps the app and manages authentication state.
 * Provides {token, user, profile, isAuthenticated, sessionExpired, login, register, logout} to useAuth().
 * Logs the user out automatically when the token expires or the backend answers a request with 401.
 */
export function AuthProvider({children}) {
    // init token state from local storage (the function form runs loadStoredToken only on the first render)
    const [token, setToken] = useState(loadStoredToken);
    // lets the login screen explain why the user was sent back to it
    const [sessionExpired, setSessionExpired] = useState(false);

    // decode JWT into user obj and cache results to prevent re-decoding token
    // str on every re-render. only runs when token changes
    // payload: {sub: username, uid: user id, role, exp}
    const user = useMemo(() => (token ? decodeToken(token): null), [token]);

    // GET /auth/me, for what isn't in the token (facility). tagged with the token it was loaded for,
    // so a stale profile is never shown after logging in as someone else
    const [me, setMe] = useState({token: null, profile: null});
    useEffect(() => {
        if (!token) {
            return;
        }
        let cancelled = false;
        apiClient.get('/auth/me')
            .then((res) => !cancelled && setMe({token, profile: res.data}))
            .catch(() => !cancelled && setMe({token, profile: null}));
        return () => {
            cancelled = true;
        };
    }, [token]);
    // undefined while loading, then {facility_id, facility_name, ...} (or null if it couldn't load)
    const profile = token && me.token === token ? me.profile : undefined;

    const storeToken = (accessToken) => {
        localStorage.setItem('accessToken', accessToken);
        setSessionExpired(false);
        setToken(accessToken);
    };

    // username can be either the username or the email.
    // POST /auth/token is FastAPI's OAuth2 password flow, which expects form fields rather than JSON.
    // a failed login rejects with the axios error, so the login form can show the message
    const login = async (username, password) => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await apiClient.post('/auth/token', formData, {
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        });
        storeToken(response.data.access_token);
    }

    // claims the account an admin created for this email; the backend returns a token, so this also logs in
    const register = async (email, password) => {
        const data = await registerAccount({email, password});
        storeToken(data.access_token);
    };

    // useCallback keeps these stable so the timer/handler effects below don't re-run every render
    const logout = useCallback(() => {
        localStorage.removeItem('accessToken');
        setToken(null);
    }, []);

    // logout + flag it, so the login screen says the session expired rather than nothing
    const expireSession = useCallback(() => {
        setSessionExpired(true);
        logout();
    }, [logout]);

    // log out automatically once the token's exp time is reached
    useEffect(() => {
        if (!user?.exp) {
            return;
        }
        const msUntilExpiry = user.exp * 1000 - Date.now();
        const timer = setTimeout(expireSession, Math.max(msUntilExpiry, 0));
        return () => clearTimeout(timer);
    }, [user, expireSession]);

    // log out if the backend rejects the token (401) before the timer fires
    useEffect(() => {
        setUnauthorizedHandler(expireSession);
        return () => setUnauthorizedHandler(null);
    }, [expireSession]);

    // bundles auth state variables and action functions into a single object to define
    // the exact interface exposed to components that are consuming this context
    const value = {token, user, profile, isAuthenticated: Boolean(token), sessionExpired, login, register, logout};

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Custom react hook to expose AuthContext to any component.
 * Simplifies context usage in child react components, and throws if used outside AuthProvider
 * so a missing provider fails loudly instead of returning null.
 * @returns {{token, user, profile, isAuthenticated, sessionExpired, login, register, logout}}
 *   user is the decoded JWT ({sub, uid, role, exp}); profile is GET /auth/me (undefined while loading)
 */
export function useAuth() {
    const context = useContext(AuthContext);
    if (context === null){
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context;
}
