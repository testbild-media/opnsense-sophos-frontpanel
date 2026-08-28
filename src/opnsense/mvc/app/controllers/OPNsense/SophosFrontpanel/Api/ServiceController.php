<?php

namespace OPNsense\SophosFrontpanel\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

class ServiceController extends ApiControllerBase
{
    private function runBackend(string $action): string
    {
        return trim((new Backend())->configdRun('sophos_frontpanel ' . $action));
    }

    public function reconfigureAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'failed', 'message' => 'POST required'];
        }

        $backend = new Backend();
        $templateResult = strtolower(trim($backend->configdRun('template reload OPNsense/SophosFrontpanel')));
        if ($templateResult !== 'ok') {
            return [
                'result' => 'failed',
                'message' => 'Unable to render Sophos Frontpanel configuration: ' . $templateResult,
            ];
        }

        return ['result' => 'ok', 'message' => $this->runBackend('restart')];
    }

    public function statusAction(): array
    {
        return ['status' => $this->runBackend('status')];
    }

    public function restartAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'failed', 'message' => 'POST required'];
        }
        return ['result' => 'ok', 'message' => $this->runBackend('restart')];
    }

    public function checkAction(): array
    {
        if (!$this->request->isPost()) {
            return ['result' => 'failed', 'message' => 'POST required'];
        }
        return ['result' => 'ok', 'message' => $this->runBackend('check')];
    }
}
