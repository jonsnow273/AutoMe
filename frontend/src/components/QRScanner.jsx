import React from 'react';

export default function QRScanner({ isOpen, onClose, qrCode, status, loading }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-dark-800 border border-dark-700 rounded-3xl p-6 max-w-md w-full shadow-2xl relative text-center">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white p-2 rounded-xl hover:bg-dark-700/50 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Header */}
        <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center mx-auto mb-3 text-sm">
          WA
        </div>
        <h3 className="text-lg font-bold text-white mb-1">Connect WhatsApp</h3>
        <p className="text-xs text-gray-400 mb-6">
          Scan the QR code with WhatsApp on your phone to link your account.
        </p>

        {/* QR Code Container */}
        <div className="w-64 h-64 mx-auto bg-white rounded-2xl p-4 flex items-center justify-center shadow-inner relative overflow-hidden border border-gray-200">
          {loading || !qrCode ? (
            <div className="flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-gray-700 font-medium">
                {status === 'initializing' ? 'Launching WhatsApp engine...' : 'Generating QR code...'}
              </p>
            </div>
          ) : (
            <img
              src={qrCode}
              alt="WhatsApp QR Code"
              className="w-full h-full object-contain animate-in zoom-in-95 duration-200"
            />
          )}
        </div>

        {/* Steps */}
        <div className="mt-6 text-left bg-dark-900/60 border border-dark-700/60 rounded-2xl p-4 space-y-2">
          <p className="text-xs font-semibold text-gray-200">How to link:</p>
          <ol className="text-[11px] text-gray-400 space-y-1.5 list-decimal list-inside leading-relaxed">
            <li>Open WhatsApp on your phone</li>
            <li>Tap <b>Settings</b> or <b>Menu (⋮)</b> → <b>Linked Devices</b></li>
            <li>Tap <b>Link a Device</b> and point camera at this QR code</li>
          </ol>
        </div>

        {/* Footer */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold text-gray-300 bg-dark-700 hover:bg-dark-600 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
