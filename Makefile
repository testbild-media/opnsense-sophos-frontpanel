PLUGIN_NAME= sophos-frontpanel
PLUGIN_VERSION!= cat ${.CURDIR}/VERSION
PLUGIN_COMMENT= Sophos SG/XG chassis LCD and button integration
PLUGIN_MAINTAINER= sophos-frontpanel@users.noreply.github.com
PLUGIN_NO_ABI= yes

.include "../../Mk/plugins.mk"
