import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen w-full flex-col items-center justify-center bg-zinc-50 p-4 text-center">
          <h1 className="mb-4 text-2xl font-bold text-red-600">Algo deu errado</h1>
          <p className="mb-6 text-muted-foreground max-w-md">
            Ocorreu um erro inesperado ao renderizar a aplicação.
          </p>
          {this.state.error && (
            <div className="mb-6 w-full max-w-2xl overflow-auto rounded bg-red-50 p-4 text-left text-xs font-mono text-red-800 border border-red-200">
              {this.state.error.toString()}
            </div>
          )}
          <button
            onClick={() => window.location.reload()}
            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors"
          >
            Recarregar Página
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
