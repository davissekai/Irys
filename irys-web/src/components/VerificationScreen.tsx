import React, { useState, useEffect } from 'react';

interface VerificationScreenProps {
    imageFile: File | null;
    columns: string[];
    initialRows: any[];
    statusMessage?: string | null;
    onBack: () => void;
    onExport: (data: any[]) => void;
}

export const VerificationScreen: React.FC<VerificationScreenProps> = ({ imageFile, columns: propColumns, initialRows, statusMessage, onBack, onExport }) => {
    const [rows, setRows] = useState<Record<string, string>[]>(initialRows || []);

    // DEBUG: Log what we receive
    console.log("[VerificationScreen] initialRows:", initialRows);
    console.log("[VerificationScreen] rows state:", rows);

    // Derive actual columns from row keys if available (most reliable)
    // This ensures columns match the exact keys in the data
    const columns = rows.length > 0
        ? Object.keys(rows[0]).filter(k => k !== '__meta')
        : propColumns;

    console.log("[VerificationScreen] columns:", columns);

    // Sync with parent when initialRows changes (e.g., after API call completes)
    useEffect(() => {
        console.log("[VerificationScreen] useEffect triggered, initialRows:", initialRows);
        if (initialRows && initialRows.length > 0) {
            setRows(initialRows);
        }
    }, [initialRows]);

    const [imageUrl] = useState<string | null>(imageFile ? URL.createObjectURL(imageFile) : null);
    const [zoom, setZoom] = useState(1);

    const updateCell = (rowIndex: number, col: string, value: string) => {
        const newRows = [...rows];
        newRows[rowIndex][col] = value;
        setRows(newRows);
    };

    const isSaving = statusMessage?.includes("Saving") || statusMessage?.includes("Exporting");

    return (
        <div className="flex flex-col h-[calc(100vh-6rem)] gap-4 animate-in fade-in duration-500">
            {/* Header Actions */}
            <div className="flex items-center justify-between border-b border-border pb-4">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    Verify Data
                    <span className="text-xs font-normal text-zinc-500 bg-zinc-900 border border-zinc-800 px-2 py-0.5 rounded-full">
                        {rows.length} rows
                    </span>
                </h2>
                <div className="flex gap-2">
                    <button
                        onClick={onBack}
                        disabled={isSaving}
                        className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors border border-transparent hover:border-zinc-800 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        &larr; Back
                    </button>
                    <button
                        onClick={() => !isSaving && onExport(rows)}
                        disabled={isSaving}
                        className={`px-4 py-2 rounded-sm text-sm font-medium shadow-lg flex items-center gap-2 transition-all ${isSaving
                                ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                                : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/20"
                            }`}
                    >
                        <span>{isSaving ? "Exporting..." : "Export Database"}</span>
                        <svg className={`w-4 h-4 ${isSaving ? "animate-pulse" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                    </button>
                </div>
            </div>

            <div className="flex-1 flex gap-6 overflow-hidden min-h-0">
                {/* Image Viewer (Left Panel) */}
                <div className="flex-1 bg-black/40 border border-border rounded-lg overflow-hidden relative group shadow-inner">
                    {imageUrl ? (
                        <div className="w-full h-full overflow-auto flex items-start justify-center p-4">
                            <img
                                src={imageUrl}
                                alt="Register Source"
                                style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
                                className="max-w-full shadow-2xl transition-transform duration-100 ease-out"
                            />
                        </div>
                    ) : (
                        <div className="flex items-center justify-center h-full text-zinc-500 flex-col gap-2">
                            <svg className="w-8 h-8 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            <span>No Image Preview</span>
                        </div>
                    )}

                    {/* Floating Image Controls */}
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-1 bg-zinc-900/90 border border-zinc-700 p-1 rounded-full opacity-0 group-hover:opacity-100 transition-all translate-y-2 group-hover:translate-y-0 shadow-xl backdrop-blur-md">
                        <button onClick={() => setZoom(z => Math.max(0.2, z - 0.2))} className="w-8 h-8 flex items-center justify-center hover:bg-zinc-700/50 rounded-full text-zinc-300 transition-colors">-</button>
                        <span className="text-xs font-mono w-12 flex items-center justify-center text-zinc-400 select-none">{Math.round(zoom * 100)}%</span>
                        <button onClick={() => setZoom(z => Math.min(3, z + 0.2))} className="w-8 h-8 flex items-center justify-center hover:bg-zinc-700/50 rounded-full text-zinc-300 transition-colors">+</button>
                    </div>
                </div>

                {/* Data Grid (Right Panel) */}
                <div className="flex-1 border border-border rounded-lg bg-surface/30 overflow-hidden flex flex-col shadow-sm">
                    {statusMessage && (
                        <div className="mx-3 mt-3 px-3 py-2 text-sm border border-amber-700/60 bg-amber-950/30 text-amber-200 rounded">
                            {statusMessage}
                        </div>
                    )}
                    <div className="overflow-auto flex-1 custom-scrollbar">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-zinc-900/90 sticky top-0 z-10 backdrop-blur-md shadow-sm">
                                <tr>
                                    <th className="p-3 border-b border-r border-border w-12 text-center text-xs text-zinc-500 font-medium">#</th>
                                    {columns.map(col => (
                                        <th key={col} className="p-3 border-b border-border text-xs font-mono uppercase text-zinc-500 min-w-[140px] font-semibold tracking-wide">
                                            {col}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-800/50">
                                {rows.length === 0 && (
                                    <tr>
                                        <td colSpan={columns.length + 1} className="p-6 text-sm text-zinc-500">
                                            No extracted rows to display yet.
                                        </td>
                                    </tr>
                                )}
                                {rows.map((row, rIdx) => (
                                    <tr key={rIdx} className="group hover:bg-zinc-800/30 transition-colors">
                                        <td className="p-2 border-r border-border text-center text-xs text-zinc-600 font-mono select-none group-hover:text-zinc-500">
                                            {rIdx + 1}
                                        </td>
                                        {columns.map(col => (
                                            <td key={col} className="p-0 relative border-r border-zinc-800/30 last:border-r-0">
                                                <input
                                                    value={(() => {
                                                        if (row[col] !== undefined) return row[col];
                                                        // Case-insensitive fallback
                                                        const key = Object.keys(row).find(k => k.toLowerCase() === col.toLowerCase());
                                                        return key ? row[key] : '';
                                                    })()}
                                                    onChange={(e) => updateCell(rIdx, col, e.target.value)}
                                                    className="w-full h-full bg-transparent px-4 py-3 text-sm text-zinc-200 outline-none focus:bg-accent/5 focus:shadow-[inset_0_0_0_1px_var(--color-accent)] transition-all font-medium placeholder-zinc-700"
                                                    spellCheck={false}
                                                    placeholder="..."
                                                    disabled={isSaving}
                                                />
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        <div className="p-3 border-t border-border bg-zinc-900/30 backdrop-blur-sm sticky bottom-0">
                            <button
                                onClick={() => setRows([...rows, {}])}
                                disabled={isSaving}
                                className="w-full py-2.5 text-xs font-medium text-zinc-500 hover:text-accent hover:bg-accent/5 hover:border-accent/40 rounded border border-dashed border-zinc-700 transition-all uppercase tracking-wide disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                                + Add Empty Row
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
