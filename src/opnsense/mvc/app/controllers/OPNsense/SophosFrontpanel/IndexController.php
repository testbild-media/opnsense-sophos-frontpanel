<?php

namespace OPNsense\SophosFrontpanel;

class IndexController extends \OPNsense\Base\IndexController
{
    public function indexAction()
    {
        $this->view->pick('OPNsense/SophosFrontpanel/index');
        $this->view->generalForm = $this->getForm('general');
    }
}
