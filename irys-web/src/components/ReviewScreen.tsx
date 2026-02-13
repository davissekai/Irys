import React, { useMemo, useState } from 'react';

interface ReviewScreenProps {
    eventName: string;
    imageFile: File;
    onRetake: () => void;
    onProceed: (file: File) => void | Promise<void>;
}

const rotateImageFile = async (file: File, quarterTurns: number): Promise<File> => {
    const turns = ((quarterTurns % 4) + 4) % 4;
    if (turns === 0) return file;

    const imageUrl = URL.createObjectURL(file);
    try {
        const img = await new Promise<HTMLImageElement>((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error('Could not load image for rotation.'));
            image.src = imageUrl;
        });

        const canvas = document.createElement('canvas');
        const swapSides = turns % 2 !== 0;
        canvas.width = swapSides ? img.height : img.width;
        canvas.height = swapSides ? img.width : img.height;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            throw new Error('Canvas context unavailable.');
        }

        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(turns * (Math.PI / 2));
        ctx.drawImage(img, -img.width / 2, -img.height / 2);

        const blob = await new Promise<Blob>((resolve, reject) => {
            canvas.toBlob((result) => {
                if (!result) {
                    reject(new Error('Could not create rotated image.'));
                    return;
                }
                resolve(result);
            }, file.type || 'image/jpeg');
        });

        return new File([blob], file.name, {
            type: blob.type || file.type || 'image/jpeg',
            lastModified: Date.now(),
        });
    } finally {
        URL.revokeObjectURL(imageUrl);
    }
};

export const ReviewScreen: React.FC<ReviewScreenProps> = ({ eventName, imageFile, onRetake, onProceed }) => {
    const [rotation, setRotation] = useState(0);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const previewUrl = useMemo(() => URL.createObjectURL(imageFile), [imageFile]);

    const handleProceed = async () => {
        setIsSubmitting(true);
        setError(null);
        try {
            const rotated = await rotateImageFile(imageFile, rotation);
            await onProceed(rotated);
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Failed to prepare image for extraction.';
            setError(message);
            setIsSubmitting(false);
        }
    };

    return (
        <div className="w-full max-w-5xl mx-auto space-y-6 py-8 animate-in fade-in duration-500">
            <div className="space-y-2">
                <h2 className="text-2xl font-bold text-white tracking-tight">Review Before Extraction</h2>
                <p className="text-zinc-400">
                    Session: <span className="text-accent font-medium">{eventName}</span>
                </p>
                <p className="text-xs font-mono text-zinc-500">
                    {imageFile.name} | {(imageFile.size / (1024 * 1024)).toFixed(2)} MB
                </p>
            </div>

            {error && (
                <div className="px-3 py-2 text-sm border border-amber-700/60 bg-amber-950/30 text-amber-200 rounded">
                    {error}
                </div>
            )}

            <div className="border border-border rounded-lg bg-black/40 min-h-[420px] flex items-center justify-center overflow-auto p-4">
                <img
                    src={previewUrl}
                    alt="Review capture"
                    style={{ transform: `rotate(${rotation * 90}deg)` }}
                    className="max-w-full max-h-[72vh] object-contain transition-transform duration-200"
                    onLoad={() => URL.revokeObjectURL(previewUrl)}
                />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setRotation((prev) => (prev + 3) % 4)}
                        disabled={isSubmitting}
                        className="px-4 py-2 text-sm border border-zinc-700 text-zinc-200 hover:bg-zinc-800 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Rotate Left
                    </button>
                    <button
                        onClick={() => setRotation((prev) => (prev + 1) % 4)}
                        disabled={isSubmitting}
                        className="px-4 py-2 text-sm border border-zinc-700 text-zinc-200 hover:bg-zinc-800 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Rotate Right
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={onRetake}
                        disabled={isSubmitting}
                        className="px-4 py-2 text-sm border border-zinc-700 text-zinc-300 hover:bg-zinc-800 rounded-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Retake
                    </button>
                    <button
                        onClick={handleProceed}
                        disabled={isSubmitting}
                        className="px-5 py-2 text-sm font-medium bg-accent hover:bg-accent-hover text-white rounded-sm disabled:bg-zinc-800 disabled:text-zinc-500 disabled:cursor-not-allowed"
                    >
                        {isSubmitting ? 'Preparing...' : 'Proceed to Extraction'}
                    </button>
                </div>
            </div>
        </div>
    );
};
