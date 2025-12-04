import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM || '',
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || '',
};

// В конструктор передаём ТОЛЬКО конфиг без pkceMethod
const keycloak = new Keycloak(keycloakConfig);

// PKCE и прочие опции — в initOptions
const keycloakProviderInitConfig = {
  onLoad: 'login-required' as const,
  checkLoginIframe: false,
  pkceMethod: 'S256' as const,
  silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
};

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={keycloakProviderInitConfig}
      autoRefreshToken={true}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;