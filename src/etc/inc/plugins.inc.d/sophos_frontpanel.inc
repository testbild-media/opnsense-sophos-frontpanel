<?php

function sophos_frontpanel_services()
{
    return [[
        'description' => gettext('Sophos Frontpanel'),
        'configd' => [
            'restart' => ['sophos_frontpanel restart'],
            'start' => ['sophos_frontpanel start'],
            'stop' => ['sophos_frontpanel stop'],
        ],
        'name' => 'sophos_frontpanel',
        'pidfile' => '/var/run/sophos_frontpanel.pid',
    ]];
}
