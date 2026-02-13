import React from 'react';
import type { ExportBatch, TableRow } from '../types';

interface HistoryScreenProps {
    eventName: string;
    batches: ExportBatch[];
    rows: TableRow[];
    selectedExportId: string | null;
    isLoading: boolean;
    error: string | null;
    onBack: () => void;
    onRefresh: () => void | Promise<void>;
    onSelectExport: (exportId: string) => void | Promise<void>;
}

const formatDateTime = (value: string): string => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
};

export const HistoryScreen: React.FC<HistoryScreenProps> = ({
    eventName,
    batches,
    rows,
    selectedExportId,
    isLoading,
    error,
    onBack,
    onRefresh,
    onSelectExport,
}) => {
    const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

    return (
        <div className="w-full max-w-7xl mx-auto h-[calc(100vh-6rem)] flex flex-col gap-4 py-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between border-b border-border pb-4">
                <div>
                    <h2 className="text-xl font-bold text-white tracking-tight">Export History</h2>
                    <p className="text-sm text-zinc-500">Event: {eventName}</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={onRefresh}
                        className="px-4 py-2 text-sm border border-zinc-700 text-zinc-200 hover:bg-zinc-800 rounded-sm"
                    >
                        Refresh
                    </button>
                    <button
                        onClick={onBack}
                        className="px-4 py-2 text-sm border border-zinc-700 text-zinc-200 hover:bg-zinc-800 rounded-sm"
                    >
                        Back to Capture
                    </button>
                </div>
            </div>

            {error && (
                <div className="px-3 py-2 text-sm border border-amber-700/60 bg-amber-950/30 text-amber-200 rounded">
                    {error}
                </div>
            )}

            <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
                <div className="border border-border rounded-lg bg-surface/30 overflow-hidden flex flex-col">
                    <div className="px-3 py-2 border-b border-border text-xs font-mono uppercase text-zinc-500">
                        Export Batches
                    </div>
                    <div className="overflow-auto flex-1">
                        {isLoading && (
                            <div className="p-4 text-sm text-zinc-500">Loading history...</div>
                        )}
                        {!isLoading && batches.length === 0 && (
                            <div className="p-4 text-sm text-zinc-500">No exports found for this event yet.</div>
                        )}
                        {!isLoading && batches.map((batch) => (
                            <button
                                key={batch.export_id}
                                onClick={() => onSelectExport(batch.export_id)}
                                className={`w-full text-left px-3 py-3 border-b border-zinc-800/60 hover:bg-zinc-800/40 transition-colors ${
                                    selectedExportId === batch.export_id ? 'bg-zinc-800/60' : ''
                                }`}
                            >
                                <div className="text-sm text-zinc-200 font-mono truncate">{batch.export_id}</div>
                                <div className="text-xs text-zinc-500 mt-1">{formatDateTime(batch.exported_at)}</div>
                                <div className="text-xs text-zinc-400 mt-1">{batch.row_count} rows</div>
                            </button>
                        ))}
                    </div>
                </div>

                <div className="border border-border rounded-lg bg-surface/30 overflow-hidden flex flex-col">
                    <div className="px-3 py-2 border-b border-border text-xs font-mono uppercase text-zinc-500">
                        Exported Rows
                    </div>
                    <div className="overflow-auto flex-1">
                        {selectedExportId && rows.length === 0 && !isLoading && (
                            <div className="p-4 text-sm text-zinc-500">No rows found for this export.</div>
                        )}
                        {!selectedExportId && !isLoading && (
                            <div className="p-4 text-sm text-zinc-500">Select an export batch to inspect rows.</div>
                        )}
                        {rows.length > 0 && (
                            <table className="w-full text-left border-collapse">
                                <thead className="bg-zinc-900/90 sticky top-0 z-10">
                                    <tr>
                                        <th className="p-3 border-b border-r border-border w-12 text-center text-xs text-zinc-500 font-medium">#</th>
                                        {columns.map((col) => (
                                            <th key={col} className="p-3 border-b border-border text-xs font-mono uppercase text-zinc-500 min-w-[140px] font-semibold tracking-wide">
                                                {col}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows.map((row, idx) => (
                                        <tr key={idx} className="border-b border-zinc-800/50">
                                            <td className="p-2 border-r border-border text-center text-xs text-zinc-600 font-mono">
                                                {idx + 1}
                                            </td>
                                            {columns.map((col) => (
                                                <td key={`${idx}-${col}`} className="p-3 text-sm text-zinc-200">
                                                    {row[col] ?? ''}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
