import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const downloadReport = async () => {
    if (!keycloak) {
      setError('Auth client is not initialized');
      return;
    }

    if (!keycloak.authenticated) {
      keycloak.login();
      return;
    }

    try {
      setLoading(true);
      setError(null);

      await keycloak.updateToken(30).catch(() => {
        keycloak.login();
        throw new Error('Session expired, redirecting to login');
      });

      const token = keycloak.token;
      if (!token) {
        throw new Error('No access token available');
      }

      const apiUrl = process.env.REACT_APP_API_URL || '';
      const response = await fetch(apiUrl + '/reports', {
        method: 'GET',
        headers: {
          Authorization: 'Bearer ' + token,
          Accept: 'text/csv,application/octet-stream',
        },
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(text || 'Request failed with status ' + response.status);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'report.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return <div>Loading...</div>;
  }

  if (!keycloak || !keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => keycloak && keycloak.login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

        <button
          onClick={downloadReport}
          disabled={loading}
          className={
            'px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ' +
            (loading ? 'opacity-50 cursor-not-allowed' : '')
          }
        >
          {loading ? 'Generating Report...' : 'Download Report'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;