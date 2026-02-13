import { useCallback, useEffect, useState } from 'react';
import { Layout } from './components/Layout';
import { EventSetup } from './components/EventSetup';
import { CaptureScreen } from './components/CaptureScreen';
import { ReviewScreen } from './components/ReviewScreen';
import { VerificationScreen } from './components/VerificationScreen';
import { HistoryScreen } from './components/HistoryScreen';
import { StartupScreen } from './components/StartupScreen';
import type { ExportBatch, ExportRowsResponse, ExportsListResponse, ExtractResponse, TableRow } from './types';

type ViewState = 'booting' | 'setup' | 'capture' | 'review' | 'verify' | 'history';

interface SessionConfig {
  eventName: string;
  columns: string[];
}

interface SessionStats {
  photosSaved: number;
  rowsSaved: number;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 90000);

function App() {
  const [view, setView] = useState<ViewState>('booting');
  const [session, setSession] = useState<SessionConfig | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [sessionStats, setSessionStats] = useState<SessionStats>({ photosSaved: 0, rowsSaved: 0 });
  const [captureNotice, setCaptureNotice] = useState<string | null>(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [rows, setRows] = useState<TableRow[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [historyBatches, setHistoryBatches] = useState<ExportBatch[]>([]);
  const [historyRows, setHistoryRows] = useState<TableRow[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedExportId, setSelectedExportId] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [isBooting, setIsBooting] = useState(false);

  const bootstrapEngine = useCallback(async () => {
    setIsBooting(true);
    setBootError(null);
    const maxAttempts = 3;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await fetch(`${API_BASE_URL}/warmup`, { method: 'POST' });
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.detail || `Warmup failed (${response.status})`);
        }
        if (!data?.ok) {
          throw new Error(data?.error || 'Warmup endpoint did not report ready state.');
        }

        setView('setup');
        setIsBooting(false);
        return;
      } catch (error) {
        if (attempt === maxAttempts) {
          const message = error instanceof Error ? error.message : 'Warmup failed.';
          setBootError(message);
          setIsBooting(false);
          return;
        }
      }
    }
  }, []);

  useEffect(() => {
    void bootstrapEngine();
  }, [bootstrapEngine]);

  const handleSetupComplete = (name: string, cols: string[]) => {
    setSession({ eventName: name, columns: cols });
    setSessionStats({ photosSaved: 0, rowsSaved: 0 });
    setCaptureNotice(null);
    setView('capture');
  };

  const resetExtractionState = () => {
    setFile(null);
    setRows([]);
    setStatusMessage(null);
  };

  const handleEndSession = (skipConfirmation = false) => {
    if (!session) return;
    if (!skipConfirmation) {
      const confirmed = window.confirm(`End session "${session.eventName}"?`);
      if (!confirmed) return;
    }
    resetExtractionState();
    setSession(null);
    setCaptureNotice(null);
    setView('setup');
  };

  const runExtraction = async (selectedFile: File) => {
    if (!session) return;
    setFile(selectedFile);
    setView('verify');
    setIsProcessing(true);
    setStatusMessage(null);
    setRows([]);
    setCaptureNotice(null);

    try {
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

      const data: ExtractResponse = await response.json();

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
        setStatusMessage('Extraction response format was invalid. Check backend logs.');
        setRows([]);
      }
    } catch (error) {
      console.error("Error extracting:", error);
      const message =
        error instanceof DOMException && error.name === 'AbortError'
          ? `Extraction timed out after ${Math.round(API_TIMEOUT_MS / 1000)}s. Verify backend reachability at ${API_BASE_URL}.`
          : error instanceof TypeError && error.message === 'Failed to fetch'
            ? `Cannot reach backend at ${API_BASE_URL}. Check server status and CORS settings.`
          : error instanceof Error
            ? error.message
            : 'Extraction failed. Check backend logs.';
      setStatusMessage(message);
      setRows([]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleImageSelected = (selectedFile: File) => {
    setFile(selectedFile);
    setStatusMessage(null);
    setRows([]);
    setCaptureNotice(null);
    setView('review');
  };

  const fetchExportRows = async (eventName: string, exportId: string) => {
    const response = await fetch(
      `${API_BASE_URL}/exports/${encodeURIComponent(eventName)}/${encodeURIComponent(exportId)}`
    );
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to load export rows (${response.status}): ${errorText}`);
    }
    const data: ExportRowsResponse = await response.json();
    const loadedRows = Array.isArray(data?.rows) ? data.rows : [];
    setHistoryRows(loadedRows);
    setSelectedExportId(exportId);
  };

  const loadHistory = async () => {
    if (!session) return;
    setHistoryLoading(true);
    setHistoryError(null);
    setHistoryRows([]);
    setSelectedExportId(null);

    try {
      const response = await fetch(`${API_BASE_URL}/exports/${encodeURIComponent(session.eventName)}`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to load exports (${response.status}): ${errorText}`);
      }

      const data: ExportsListResponse = await response.json();
      const exportsList = Array.isArray(data?.exports) ? data.exports : [];
      setHistoryBatches(exportsList);

      if (exportsList.length > 0 && typeof exportsList[0].export_id === 'string') {
        await fetchExportRows(session.eventName, exportsList[0].export_id);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load export history.';
      setHistoryError(message);
      setHistoryBatches([]);
      setHistoryRows([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const openHistory = async () => {
    setView('history');
    await loadHistory();
  };

  const handleExport = async (data: TableRow[], nextStep: 'continue' | 'end') => {
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
      const savedRows = Array.isArray(data) ? data.length : 0;
      setSessionStats(prev => ({
        photosSaved: prev.photosSaved + 1,
        rowsSaved: prev.rowsSaved + savedRows,
      }));
      setStatusMessage(null);

      if (nextStep === 'continue') {
        resetExtractionState();
        setCaptureNotice(result.message || `Saved ${savedRows} rows. Capture the next photo.`);
        setView('capture');
      } else {
        alert(result.message || "Data successfully exported to Supabase!");
        handleEndSession(true);
      }
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
            sessionStats={sessionStats}
            notice={captureNotice}
            onImageSelected={handleImageSelected}
            onViewHistory={openHistory}
            onEndSession={handleEndSession}
          />
        );
      case 'review':
        if (!session || !file) return null;
        return (
          <ReviewScreen
            eventName={session.eventName}
            imageFile={file}
            onRetake={() => {
              setFile(null);
              setView('capture');
            }}
            onProceed={(reviewedFile) => runExtraction(reviewedFile)}
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
            key={file ? `${file.name}-${file.lastModified}` : 'verify-empty'}
            imageFile={file}
            initialRows={rows}
            columns={session.columns}
            statusMessage={statusMessage}
            onBack={() => setView('capture')}
            onSaveAndContinue={(data: TableRow[]) => handleExport(data, 'continue')}
            onSaveAndEnd={(data: TableRow[]) => handleExport(data, 'end')}
          />
        );
      case 'history':
        if (!session) return null;
        return (
          <HistoryScreen
            eventName={session.eventName}
            batches={historyBatches}
            rows={historyRows}
            selectedExportId={selectedExportId}
            isLoading={historyLoading}
            error={historyError}
            onBack={() => setView('capture')}
            onRefresh={loadHistory}
            onSelectExport={(exportId) => fetchExportRows(session.eventName, exportId)}
          />
        );
      case 'booting':
        return (
          <StartupScreen
            error={bootError}
            isRetrying={isBooting}
            onRetry={() => {
              void bootstrapEngine();
            }}
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
