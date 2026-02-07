import React from 'react';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    return (
        <div className="min-h-screen bg-background text-zinc-100 flex flex-col font-sans selection:bg-accent selection:text-white">
            {/* Header */}
            <header className="h-14 border-b border-border flex items-center px-6 bg-surface/50 backdrop-blur-sm fixed w-full top-0 z-50">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-accent rounded-sm shadow-[0_0_8px_rgba(14,165,233,0.4)]"></div>
                    <span className="font-bold tracking-tight text-sm uppercase text-zinc-400">Project Irys</span>
                </div>
                <div className="ml-auto flex items-center gap-4 text-xs font-mono text-zinc-500">
                    <span>v0.1.0-alpha</span>
                    <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                        <span>System Online</span>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 pt-14 flex flex-col p-6">
                <div className="w-full max-w-7xl mx-auto h-full flex flex-col relative animate-in fade-in duration-500">
                    {children}
                </div>
            </main>
        </div>
    );
};
