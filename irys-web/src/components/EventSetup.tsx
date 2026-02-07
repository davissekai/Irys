import React, { useState } from 'react';

interface EventSetupProps {
    onComplete: (eventName: string, columns: string[]) => void;
}

export const EventSetup: React.FC<EventSetupProps> = ({ onComplete }) => {
    const [eventName, setEventName] = useState('');
    const [columns, setColumns] = useState<string[]>(['Name', 'Phone']); // Default defaults to guide user
    const [newCol, setNewCol] = useState('');

    const addColumn = () => {
        if (newCol.trim() && !columns.includes(newCol.trim())) {
            setColumns([...columns, newCol.trim()]);
            setNewCol('');
        }
    };

    const removeColumn = (col: string) => {
        setColumns(columns.filter(c => c !== col));
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addColumn();
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 py-10">
            <div className="space-y-2 border-b border-border pb-6">
                <h2 className="text-2xl font-bold text-white tracking-tight">Event Configuration</h2>
                <p className="text-zinc-400">Define the schema for today's register.</p>
            </div>

            <div className="space-y-8">
                {/* Event Name */}
                <div className="space-y-2">
                    <label className="text-xs font-mono uppercase text-zinc-500 tracking-wider font-semibold">Event Name</label>
                    <input
                        type="text"
                        value={eventName}
                        onChange={(e) => setEventName(e.target.value)}
                        placeholder="e.g. Workshop Registration - Day 1"
                        className="w-full bg-surface border border-border p-4 text-white placeholder-zinc-600 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all rounded-sm text-lg"
                        autoFocus
                    />
                </div>

                {/* Columns Input */}
                <div className="space-y-3">
                    <div className="flex justify-between items-baseline">
                        <label className="text-xs font-mono uppercase text-zinc-500 tracking-wider font-semibold">
                            Captured Columns <span className="text-accent ml-1">[{columns.length}]</span>
                        </label>
                        <span className="text-xs text-zinc-600">Press Enter to add</span>
                    </div>

                    <div className="flex gap-0 shadow-sm">
                        <input
                            type="text"
                            value={newCol}
                            onChange={(e) => setNewCol(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Type column header & press Enter..."
                            className="flex-1 bg-surface border border-border border-r-0 p-3 text-white placeholder-zinc-600 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all rounded-l-sm"
                        />
                        <button
                            onClick={addColumn}
                            className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 border border-border text-zinc-300 transition-colors rounded-r-sm cursor-pointer font-medium uppercase text-xs tracking-wide"
                        >
                            Add
                        </button>
                    </div>

                    {/* Chips */}
                    <div className="flex flex-wrap gap-2 pt-2 min-h-[40px]">
                        {columns.length === 0 && (
                            <div className="w-full p-4 border border-dashed border-zinc-800 rounded text-center text-zinc-600 text-sm">
                                No columns defined. Add headers appearing on the paper.
                            </div>
                        )}
                        {columns.map((col) => (
                            <div
                                key={col}
                                className="group flex items-center gap-2 bg-zinc-900/50 border border-zinc-800 text-zinc-300 px-3 py-1.5 rounded-sm text-sm hover:border-zinc-700 transition-colors select-none"
                            >
                                <span>{col}</span>
                                <button
                                    onClick={() => removeColumn(col)}
                                    className="text-zinc-600 hover:text-red-400 ml-1 transition-colors cursor-pointer w-4 h-4 flex items-center justify-center rounded hover:bg-red-900/20"
                                >
                                    &times;
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="pt-12 flex justify-end border-t border-border mt-8">
                <button
                    onClick={() => onComplete(eventName, columns)}
                    disabled={!eventName || columns.length === 0}
                    className="px-8 py-3 bg-accent hover:bg-accent-hover disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-white font-medium rounded-sm transition-all shadow-lg shadow-accent/10 hover:shadow-accent/20 cursor-pointer text-sm uppercase tracking-wide flex items-center gap-2"
                >
                    Initialize Session <span className="text-lg">&rarr;</span>
                </button>
            </div>
        </div>
    );
};
