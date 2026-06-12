import { motion } from "framer-motion";

const loadingMessages = ["Изучаем вкус...", "Подбираем совпадения...", "Проверяем, где посмотреть..."];

export function LoadingStage() {
  return (
    <div className="flex min-h-[280px] flex-col items-center justify-center gap-6 rounded-3xl border border-white/10 bg-surface/70 p-8 shadow-card">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 2.4, ease: "linear" }}
        className="h-20 w-20 rounded-full border-4 border-accent/30 border-t-accent"
      />
      <div className="space-y-2 text-center">
        {loadingMessages.map((message, index) => (
          <motion.p
            key={message}
            animate={{ opacity: [0.35, 1, 0.35] }}
            transition={{ repeat: Infinity, duration: 1.8, delay: index * 0.2 }}
            className="text-sm text-zinc-200"
          >
            {message}
          </motion.p>
        ))}
      </div>
    </div>
  );
}
