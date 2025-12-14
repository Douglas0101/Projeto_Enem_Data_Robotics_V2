import { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./ui/button";

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
  onRetry?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

/**
 * Error Boundary especializado para componentes de visualização (charts, maps).
 * 
 * Captura erros de renderização e exibe um fallback amigável,
 * evitando que um erro em um gráfico quebre toda a aplicação.
 */
export class ChartErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    this.setState({ errorInfo });
    
    // Log para debugging
    console.error("[ChartErrorBoundary] Erro capturado:", error);
    console.error("[ChartErrorBoundary] Component Stack:", errorInfo.componentStack);
    
    // TODO: Integrar com Sentry ou outro serviço de monitoramento
    // if (typeof window !== 'undefined' && (window as any).Sentry) {
    //   (window as any).Sentry.captureException(error, { extra: { errorInfo } });
    // }
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    this.props.onRetry?.();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-64 bg-red-50 rounded-lg border border-red-200 p-6">
          <AlertTriangle className="h-10 w-10 text-red-500 mb-3" />
          <p className="text-red-700 font-medium text-center mb-2">
            {this.props.fallbackMessage || "Erro ao carregar visualização"}
          </p>
          <p className="text-red-500 text-sm text-center mb-4 max-w-md">
            {this.state.error?.message || "Ocorreu um erro inesperado ao renderizar este componente."}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={this.handleRetry}
            className="text-red-600 border-red-300 hover:bg-red-100"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Tentar Novamente
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ChartErrorBoundary;
