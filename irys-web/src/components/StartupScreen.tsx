import React from 'react';

interface StartupScreenProps {
    error?: string | null;
    onRetry: () => void;
    isRetrying: boolean;
}

export const StartupScreen: React.FC<StartupScreenProps> = ({ error, onRetry, isRetrying }) => {
    return (
        <div className="min-h-[70vh] flex flex-col items-center justify-center gap-6 animate-in fade-in duration-500">
            <div className="relative">
                <div className="w-20 h-20 rounded-full border-2 border-zinc-800 border-t-accent animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-2.5 h-2.5 bg-accent rounded-full animate-pulse"></div>
                </div>
            </div>

            <div className="text-center space-y-2 max-w-md">
                <h2 className="text-2xl font-bold text-white tracking-tight">Starting extraction engine</h2>
                <p className="text-sm text-zinc-500 font-mono">
                    Preparing backend OCR services. Please wait...
                </p>
            </div>

            {error && (
                <div className="w-full max-w-xl px-4 py-3 text-sm border border-amber-700/60 bg-amber-950/30 text-amber-200 rounded">
                    <div className="font-medium">Could not warm up extraction engine.</div>
                    <div className="mt-1 opacity-90">{error}</div>
                </div>
            )}

            <button
                onClick={onRetry}
                disabled={isRetrying}
                className="px-5 py-2 text-sm font-medium bg-accent hover:bg-accent-hover text-white rounded-sm disabled:bg-zinc-800 disabled:text-zinc-500 disabled:cursor-not-allowed"
            >
                {isRetrying ? 'Retrying...' : 'Retry Startup'}
            </button>
        </div>
    );
};
