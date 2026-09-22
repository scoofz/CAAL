'use client';

import { useState } from 'react';
import { useLocale } from 'next-intl';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { SessionView } from '@/components/app/session-view';
import { WelcomeView } from '@/components/app/welcome-view';
import { MemoryPanel } from '@/components/memory';
import { SettingsPanel } from '@/components/settings/settings-panel';
import { ToolsPanel } from '@/components/tools';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(SessionView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start, end } = useSessionContext();
  const locale = useLocale();
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);

  const startCall = async () => {
    setConnectionError(null);
    const french = locale === 'fr';
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setConnectionError(
        french
          ? 'Le microphone exige HTTPS sur les autres machines. Sur la VM, utilisez http://localhost:3000 ; à distance, utilisez HTTPS avec un certificat approuvé.'
          : 'Microphone access requires HTTPS on other machines. On the VM use http://localhost:3000; remotely use HTTPS with a trusted certificate.'
      );
      return;
    }
    try {
      // Establish microphone permission before connecting, so a failed capture
      // cannot leave a connected session with no published microphone track.
      const capture = await navigator.mediaDevices.getUserMedia({ audio: true });
      capture.getTracks().forEach((track) => track.stop());
      await start({ tracks: { microphone: { enabled: true } } });
    } catch (error) {
      await end();
      const name = error instanceof Error ? error.name : '';
      const details =
        name === 'NotAllowedError'
          ? french
            ? 'Autorisez le microphone dans les permissions du site et du système.'
            : 'Allow microphone access in site and system permissions.'
          : name === 'NotFoundError'
            ? french
              ? 'Aucun microphone disponible : vérifiez le périphérique d’entrée.'
              : 'No microphone found: check your input device.'
            : name === 'NotReadableError'
              ? french
                ? 'Le microphone est indisponible ou utilisé par une autre application.'
                : 'The microphone is unavailable or in use by another application.'
              : french
                ? 'Vérifiez le microphone et la connexion au serveur.'
                : 'Check the microphone and server connection.';
      setConnectionError(
        `${french ? 'Impossible de démarrer la conversation.' : 'Unable to start conversation.'} ${details}`
      );
      console.error('Voice session startup failed', error);
    }
  };

  return (
    <>
      {connectionError && (
        <div
          role="alert"
          className="bg-background fixed bottom-6 left-1/2 z-50 w-[90%] max-w-xl -translate-x-1/2 rounded-lg border border-red-500 p-4 text-center text-sm"
        >
          {connectionError}
        </div>
      )}
      <AnimatePresence mode="wait">
        {/* Welcome view */}
        {!isConnected && (
          <MotionWelcomeView
            key="welcome"
            {...VIEW_MOTION_PROPS}
            onStartCall={() => void startCall()}
            onOpenSettings={() => setSettingsOpen(true)}
            onOpenTools={() => setToolsOpen(true)}
            onOpenMemory={() => setMemoryOpen(true)}
          />
        )}
        {/* Session view */}
        {isConnected && (
          <MotionSessionView
            key="session-view"
            {...VIEW_MOTION_PROPS}
            appConfig={appConfig}
            onOpenMemory={() => setMemoryOpen(true)}
          />
        )}
      </AnimatePresence>

      {/* Settings panel */}
      <SettingsPanel isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />

      {/* Tools panel */}
      <ToolsPanel isOpen={toolsOpen} onClose={() => setToolsOpen(false)} />

      {/* Memory panel */}
      <MemoryPanel isOpen={memoryOpen} onClose={() => setMemoryOpen(false)} />
    </>
  );
}
