<template>
    <GeneralEdit :config="config"/>
</template>

<script>

import GeneralEdit from '@/components/general/edit/basic'
export default {

    components: {
        GeneralEdit,
    },

    data() {
        return {
            config: {
                name: 'Edit Setting',
                type: 'settings',
                forceReturn: true,
                editors: [
                    {
                        title: "Setting",
                        edit: "text",
                        attribute: "name",
                        titleMode: "append",
                        regex: '^[\\w\\s!?|\'\\[\\]\\+\\-=@#$%\^&*\\(\\)\\,\\.:;|]{3,32}$',
                    },
                    {
                        title: "Value",
                        edit: "text",
                        attribute: "value",
                        titleMode: "append",
                        regex: '^[\\w\\s!?|\'\\[\\]\\+\\-=@#$%\^&*\\(\\)\\,\\.:;|]{3,32}$',
                    }
               
                ]
            }
        }
    }
}
</script>

<style>

</style>
