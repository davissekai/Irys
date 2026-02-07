import React, { useRef, useState } from 'react';

interface CaptureScreenProps {
    eventName: string;
    onImageSelected: (file: File) => void;
}

export const CaptureScreen: React.FC<CaptureScreenProps> = ({ eventName, onImageSelected }) => {
    const [isDragOver, setIsDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onImageSelected(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            onImageSelected(e.target.files[0]);
        }
    };

    return (
        <div className="w-full max-w-xl mx-auto space-y-8 animate-in fade-in duration-500 py-10">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-bold text-white tracking-tight">Upload Register</h2>
                <p className="text-zinc-400">
                    Session: <span className="text-accent font-medium">{eventName}</span>
                </p>
            </div>

            <div
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
            border-2 border-dashed rounded-lg p-12 text-center transition-all duration-200 cursor-pointer
            flex flex-col items-center justify-center gap-6 min-h-[360px] relative overflow-hidden
            ${isDragOver
                        ? 'border-accent bg-accent/5 scale-[1.01]'
                        : 'border-zinc-800 hover:border-zinc-600 hover:bg-zinc-800/30'
                    }
        `}
            >
                <div className={`p-5 rounded-full bg-zinc-900 border border-zinc-700 transition-transform duration-300 ${isDragOver ? 'scale-110 shadow-lg shadow-accent/20 border-accent' : ''}`}>
                    <svg className={`w-8 h-8 ${isDragOver ? 'text-accent' : 'text-zinc-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </div>

                <div className="space-y-2 z-10">
                    <p className="text-xl font-medium text-zinc-200">Tap to take photo</p>
                    <p className="text-sm text-zinc-500">or drop image file here</p>
                </div>

                {/* Decorative Grid Background */}
                <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
                    style={{ backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)', backgroundSize: '16px 16px' }}>
                </div>

                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept="image/*"
                    capture="environment"
                    onChange={handleChange}
                />
            </div>

            <div className="flex justify-center">
                <div className="flex items-center gap-2 text-xs text-zinc-600">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></div>
                    Waiting for input
                </div>
            </div>
        </div>
    );
};
