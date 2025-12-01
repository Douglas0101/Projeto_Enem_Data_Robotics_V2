import { useState, useRef } from "react";
import { Send, Bot, User, Sparkles, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetTrigger,
} from "./ui/sheet";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { apiClient } from "../api/client";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isError?: boolean;
}

export function AIChatAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Olá! Sou o assistente inteligente do Data Robotics. Posso analisar os dados do ENEM em tempo real. Experimente perguntar 'Qual a média de matemática em SP em 2023?' ou 'Mostre a evolução das notas de redação'.",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userText = inputValue;
    setInputValue(""); // Limpa input imediatamente

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    try {
      // Chama a API real
      const response = await apiClient.post<{ response: string }>("/chat/message", {
        message: userText,
      });

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.data.response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      console.error("Erro ao enviar mensagem:", error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Desculpe, encontrei um erro ao processar sua solicitação. Verifique se o servidor backend está rodando e se a chave de API está configurada.",
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !isTyping) {
      handleSendMessage();
    }
  };

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="default" size="sm" className="gap-2 shadow-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white border-0">
          <Sparkles className="h-4 w-4" />
          <span className="hidden sm:inline">Data AI</span>
        </Button>
      </SheetTrigger>
      <SheetContent className="flex w-[400px] flex-col sm:w-[600px]">
        <SheetHeader className="border-b pb-4">
          <SheetTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-blue-600" />
            Assistente Data Robotics
          </SheetTitle>
          <SheetDescription>
            Análise de dados em tempo real com SQL via Gemini Flash 2.0
          </SheetDescription>
        </SheetHeader>
        
        <ScrollArea className="flex-1 pr-4 -mr-4" ref={scrollRef}>
          <div className="flex flex-col gap-6 py-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                <Avatar className={`h-8 w-8 border ${msg.role === "assistant" ? "bg-blue-50" : "bg-gray-100"}`}>
                    {msg.role === "assistant" ? (
                         <AvatarImage src="/bot-avatar.png" /> 
                    ) : null}
                    <AvatarFallback className={msg.role === "assistant" ? "text-blue-600 bg-blue-50" : "text-gray-600"}>
                        {msg.role === "assistant" ? <Bot className="h-5 w-5" /> : <User className="h-5 w-5" />}
                    </AvatarFallback>
                </Avatar>
                
                <div
                  className={`rounded-lg px-4 py-3 text-sm shadow-sm max-w-[85%] ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : msg.isError 
                        ? "bg-red-50 text-red-800 border border-red-200"
                        : "bg-muted/50 text-foreground border"
                  }`}
                >
                  {msg.role === "assistant" && !msg.isError ? (
                     <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-gray-900 prose-pre:text-gray-50">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                           {msg.content}
                        </ReactMarkdown>
                     </div>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex gap-3">
                 <Avatar className="h-8 w-8 border bg-blue-50">
                    <AvatarFallback className="text-blue-600 bg-blue-50">
                        <Bot className="h-5 w-5" />
                    </AvatarFallback>
                </Avatar>
                <div className="flex items-center gap-1 rounded-lg bg-muted/50 border px-4 py-3 h-[46px]">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.3s]"></span>
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400 [animation-delay:-0.15s]"></span>
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400"></span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <SheetFooter className="pt-4 border-t">
          <div className="flex w-full items-center gap-2">
            <Input
              placeholder="Digite sua pergunta sobre os dados..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isTyping}
              className="flex-1"
              autoFocus
            />
            <Button onClick={handleSendMessage} disabled={isTyping || !inputValue.trim()} size="icon">
              <Send className="h-4 w-4" />
              <span className="sr-only">Enviar</span>
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}