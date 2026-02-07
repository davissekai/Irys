import { useState } from 'react';
import { Layout } from './components/Layout';
import { EventSetup } from './components/EventSetup';
import { CaptureScreen } from './components/CaptureScreen';
import { VerificationScreen } from './components/VerificationScreen';

type ViewState = 'setup' | 'capture' | 'verify';

interface SessionConfig {
  eventName: string;
  columns: string[];
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 90000);

function App() {
  const [view, setView] = useState<ViewState>('setup');
  const [session, setSession] = useState<SessionConfig | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [rows, setRows] = useState<any[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleSetupComplete = (name: string, cols: string[]) => {
    setSession({ eventName: name, columns: cols });
    setView('capture');
  };

  const handleImageSelected = async (selectedFile: File) => {
    setFile(selectedFile);
    setView('verify');
    setIsProcessing(true);
    setStatusMessage(null);
    setRows([]);

    try {
      if (!session) return;

      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('columns', JSON.stringify(session.columns));

      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);

      let response: Response;
      try {
        response = await fetch(`${API_BASE_URL}/extract`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });
      } finally {
        window.clearTimeout(timeoutId);
      }

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Extraction failed (${response.status}): ${errorText}`);
      }

      const data = await response.json();
      console.log("API Result:", data);

      const table = data?.table ?? (Array.isArray(data?.rows) ? { rows: data.rows, headers: data.headers || [] } : null);

      if (table && Array.isArray(table.rows)) {
        const validRows = table.rows;
        const apiHeaders = Array.isArray(table.headers) ? table.headers : [];

        if (apiHeaders.length > 0) {
          setSession(prev => prev ? { ...prev, columns: apiHeaders } : null);
        }

        if (validRows.length === 0) {
          setStatusMessage(data?.error || 'No rows were extracted from this image.');
        }

        setRows(validRows);
      } else {
        console.error("Unexpected data format", data);
        setStatusMessage('Extraction response format was invalid. Check backend logs.');
        setRows([]);
      }
    } catch (error) {
      console.error("Error extracting:", error);
      const message =
        error instanceof DOMException && error.name === 'AbortError'
          ? `Extraction timed out after ${Math.round(API_TIMEOUT_MS / 1000)}s. Verify backend reachability at ${API_BASE_URL}.`
          : error instanceof Error
            ? error.message
            : 'Extraction failed. Check backend logs.';
      setStatusMessage(message);
      setRows([]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExport = async (data: any[]) => {
    if (!session) return;
    setIsProcessing(true);
    setStatusMessage("Saving to database...");

    try {
      const response = await fetch(`${API_BASE_URL}/export-db`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          eventName: session.eventName,
          rows: data
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Export failed: ${errorText}`);
      }

      const result = await response.json();
      alert(result.message || "Data successfully exported to Supabase!");
      setStatusMessage(null);
    } catch (error) {
      console.error("Export error:", error);
      alert(error instanceof Error ? error.message : "Failed to export data to database.");
      setStatusMessage("Export failed. Please check console.");
    } finally {
      setIsProcessing(false);
    }
  };

  const renderView = () => {
    switch (view) {
      case 'setup':
        return <EventSetup onComplete={handleSetupComplete} />;
      case 'capture':
        return (
          <CaptureScreen
            eventName={session?.eventName || "New Event"}
            onImageSelected={handleImageSelected}
          />
        );
      case 'verify':
        if (!session) return null;

        if (isProcessing) {
          return (
            <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-6 animate-in fade-in duration-500">
              <div className="relative">
                <div className="w-16 h-16 rounded-full border-2 border-zinc-800 border-t-accent animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-2 h-2 bg-accent rounded-full animate-pulse"></div>
                </div>
              </div>
              <div className="text-center space-y-1">
                <h2 className="text-xl font-bold text-white tracking-tight">Extracting Data</h2>
                <p className="text-zinc-500 text-sm font-mono">Running OCR pipeline...</p>
              </div>
            </div>
          );
        }

        return (
          <VerificationScreen
            imageFile={file}
            initialRows={rows}
            columns={session.columns}
            statusMessage={statusMessage}
            onBack={() => setView('capture')}
            onExport={handleExport}
          />
        );
    }
  };

  return (
    <Layout>
      {renderView()}
    </Layout>
  );
}

export default App;
